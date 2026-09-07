# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
from unittest import IsolatedAsyncioTestCase

from superdesk.ai.errors import AIErrorKind, AIProviderError, NotSupportedError
from superdesk.ai.models import AIActionType
from superdesk.ai.prompts import (
    JSON_CONTRACT,
    SUPPORTED_ACTION_TYPES,
    parse_suggestions,
    render_system_prompt,
    render_user_message,
)

JSON_LINE = (
    'Answer with a JSON object and nothing else, of the form {"suggestions": ["first", "second"]}, '
    "with one entry per version and no formatting inside the entries."
)
FACTS_LINE = "Use only the facts of the article the user sends, do not add any of your own."


class RenderSystemPromptTestCase(IsolatedAsyncioTestCase):
    async def test_suggestion_prompt_asks_for_the_count_and_names_the_output_field(self):
        prompt = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3)

        self.assertEqual(
            prompt,
            "\n".join(
                [
                    "You are an experienced news editor. Write 3 alternative versions of the "
                    "'headline' of the article the user sends.",
                    FACTS_LINE,
                    JSON_LINE,
                ]
            ),
        )

    async def test_summary_prompt_asks_for_a_summary_and_names_the_output_field(self):
        prompt = render_system_prompt(AIActionType.SUMMARY, output_field="abstract", count=1)

        self.assertEqual(
            prompt,
            "\n".join(
                [
                    "You are an experienced news editor. Write a summary of the article the user sends, "
                    "to be used as its 'abstract'.",
                    FACTS_LINE,
                    JSON_LINE,
                ]
            ),
        )

    async def test_the_character_limit_is_only_in_the_prompt_when_the_action_has_one(self):
        with_limit = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3, max_characters=60)
        without_limit = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3)

        self.assertIn("Keep every version under 60 characters.", with_limit)
        self.assertNotIn("characters", without_limit)

    async def test_the_language_is_only_in_the_prompt_when_one_is_known(self):
        with_language = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3, language="fi")
        without_language = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3)

        self.assertIn("Write every version in fi.", with_language)
        self.assertNotIn("Write every version in", without_language)

    async def test_a_custom_system_prompt_replaces_the_template_but_keeps_the_answer_format(self):
        prompt = render_system_prompt(
            AIActionType.SUGGESTION,
            output_field="headline",
            count=3,
            system_prompt="Write tabloid headlines.",
        )

        self.assertEqual(prompt, "\n".join(["Write tabloid headlines.", FACTS_LINE, JSON_LINE]))

    async def test_an_action_type_without_a_template_is_not_supported(self):
        for action_type in (AIActionType.REWRITE, AIActionType.TRANSLATION):
            with self.subTest(action_type=action_type):
                self.assertNotIn(action_type, SUPPORTED_ACTION_TYPES)

                with self.assertRaises(NotSupportedError) as context:
                    render_system_prompt(action_type, output_field="body_html", count=1)

                self.assertEqual(context.exception.status_code, 400)
                self.assertIn(action_type.value, context.exception.message)

    async def test_the_json_contract_keeps_its_braces(self):
        prompt = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3)

        self.assertIn('{"suggestions": ["first", "second"]}', JSON_CONTRACT)
        self.assertIn('{"suggestions": ["first", "second"]}', prompt)


class RenderUserMessageTestCase(IsolatedAsyncioTestCase):
    async def test_a_single_field_is_sent_without_its_name(self):
        message = render_user_message({"body_html": "The council met on Tuesday."})

        self.assertEqual(message, "The council met on Tuesday.")

    async def test_several_fields_are_each_prefixed_with_their_name(self):
        message = render_user_message({"headline": "Council meets", "body_html": "The council met."})

        self.assertEqual(message, "headline:\nCouncil meets\n\nbody_html:\nThe council met.")


class ParseSuggestionsTestCase(IsolatedAsyncioTestCase):
    async def test_suggestions_are_read_from_the_json_contract(self):
        content = '{"suggestions": ["Council meets", "Council votes"]}'

        self.assertEqual(parse_suggestions(content, 3), ["Council meets", "Council votes"])

    async def test_suggestions_are_read_from_json_wrapped_in_a_code_fence(self):
        content = '```json\n{"suggestions": ["Council meets"]}\n```'

        self.assertEqual(parse_suggestions(content, 3), ["Council meets"])

    async def test_json_entries_that_are_not_text_are_dropped(self):
        content = '{"suggestions": ["Council meets", {"text": "Council votes"}, null]}'

        self.assertEqual(parse_suggestions(content, 3), ["Council meets"])

    async def test_an_answer_that_is_not_json_is_read_one_suggestion_per_line(self):
        content = "Council meets\n\nCouncil votes\n"

        self.assertEqual(parse_suggestions(content, 3), ["Council meets", "Council votes"])

    async def test_numbered_list_markers_are_stripped_from_a_line_answer(self):
        content = "1. Council meets\n2) Council votes"

        self.assertEqual(parse_suggestions(content, 3), ["Council meets", "Council votes"])

    async def test_the_prose_around_a_marked_list_is_not_read_as_a_suggestion(self):
        content = "Here are 3 headlines:\n1. Alpha\n2. Beta\n3. Gamma"

        self.assertEqual(parse_suggestions(content, 3), ["Alpha", "Beta", "Gamma"])

    async def test_quotes_around_a_whole_line_answer_are_stripped(self):
        content = "- \"Council meets\"\n- 'Council votes'\n- “Council adjourns”"

        self.assertEqual(parse_suggestions(content, 3), ["Council meets", "Council votes", "Council adjourns"])

    async def test_a_line_answer_that_quotes_someone_keeps_its_quotes(self):
        content = '- "Yes," she said, "again"'

        self.assertEqual(parse_suggestions(content, 3), ['"Yes," she said, "again"'])

    async def test_quotes_inside_a_json_entry_are_never_stripped(self):
        content = json.dumps({"suggestions": ['"Yes," she said, "again"', "'Brexit' means 'Brexit'", '"Alpha"']})

        self.assertEqual(
            parse_suggestions(content, 3),
            ['"Yes," she said, "again"', "'Brexit' means 'Brexit'", '"Alpha"'],
        )

    async def test_a_json_object_holding_a_single_string_is_read_as_one_suggestion(self):
        content = json.dumps({"summary": "The council met."})

        self.assertEqual(parse_suggestions(content, 3), ["The council met."])

    async def test_a_json_object_holding_a_list_of_strings_is_read_as_the_suggestions(self):
        content = json.dumps({"model": "gpt-4o", "headlines": ["Alpha", "Beta"]})

        self.assertEqual(parse_suggestions(content, 3), ["Alpha", "Beta"])

    async def test_a_bare_json_list_of_strings_is_read_as_the_suggestions(self):
        content = json.dumps(["Alpha", "Beta"])

        self.assertEqual(parse_suggestions(content, 3), ["Alpha", "Beta"])

    async def test_json_of_a_shape_no_suggestions_can_be_read_from_is_an_invalid_response(self):
        content = json.dumps({"result": {"headline": "Alpha"}})

        with self.assertRaises(AIProviderError) as context:
            parse_suggestions(content, 3)

        self.assertEqual(context.exception.kind, AIErrorKind.INVALID_RESPONSE)

    async def test_json_of_another_shape_is_not_read_line_by_line(self):
        content = json.dumps({"choices": [{"text": "Alpha"}]})

        with self.assertRaises(AIProviderError):
            parse_suggestions(content, 3)

    async def test_only_the_requested_number_of_suggestions_is_returned(self):
        content = '{"suggestions": ["One", "Two", "Three", "Four"]}'

        self.assertEqual(parse_suggestions(content, 2), ["One", "Two"])

    async def test_an_empty_answer_produces_no_suggestions(self):
        self.assertEqual(parse_suggestions("", 3), [])
        self.assertEqual(parse_suggestions('{"suggestions": []}', 3), [])
