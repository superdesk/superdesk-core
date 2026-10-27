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
    language_name,
    parse_suggestions,
    parse_translation,
    render_system_prompt,
    render_user_message,
)
from superdesk.errors import SuperdeskApiError

JSON_LINE = (
    'Answer with a JSON object and nothing else, of the form {"suggestions": ["first", "second"]}, '
    "with one entry per version and no formatting inside the entries."
)
FACTS_LINE = "Use only the facts of the article the user sends, do not add any of your own."
TRANSLATION_LINE = (
    "Keep every paragraph and all HTML markup exactly as they are and translate only the text. "
    "Keep names and figures as they are. Add nothing and leave nothing out. "
    "When the text has several fields, each introduced by its name, keep every name untranslated and in its place."
)


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
        self.assertNotIn(AIActionType.REWRITE, SUPPORTED_ACTION_TYPES)

        with self.assertRaises(NotSupportedError) as context:
            render_system_prompt(AIActionType.REWRITE, output_field="body_html", count=1)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn(AIActionType.REWRITE.value, context.exception.message)

    async def test_the_json_contract_keeps_its_braces(self):
        prompt = render_system_prompt(AIActionType.SUGGESTION, output_field="headline", count=3)

        self.assertIn('{"suggestions": ["first", "second"]}', JSON_CONTRACT)
        self.assertIn('{"suggestions": ["first", "second"]}', prompt)


class RenderTranslationPromptTestCase(IsolatedAsyncioTestCase):
    async def test_translation_is_a_supported_action_type(self):
        self.assertIn(AIActionType.TRANSLATION, SUPPORTED_ACTION_TYPES)

    async def test_translation_prompt_names_the_language_and_asks_for_plain_text(self):
        prompt = render_system_prompt(AIActionType.TRANSLATION, output_field="body_html", count=1, language="German")

        self.assertEqual(
            prompt,
            "\n".join(
                [
                    "You are an experienced news translator. Translate the article the user sends into German, "
                    "to be used as its 'body_html'.",
                    TRANSLATION_LINE,
                    "Answer with the German translation and nothing else: no introduction, no notes, no code fences.",
                ]
            ),
        )
        self.assertNotIn(JSON_CONTRACT, prompt)
        self.assertNotIn(FACTS_LINE, prompt)

    async def test_a_language_code_is_named_in_the_translation_prompt(self):
        prompt = render_system_prompt(AIActionType.TRANSLATION, output_field="body_html", count=1, language="de")

        self.assertIn("into German,", prompt)
        self.assertIn("Answer with the German translation", prompt)

    async def test_the_system_prompt_of_a_translation_is_appended_as_style_guidance(self):
        prompt = render_system_prompt(
            AIActionType.TRANSLATION,
            output_field="body_html",
            count=1,
            language="fr",
            system_prompt="  Use the agency's wire style.  ",
        )

        lines = prompt.split("\n")
        self.assertTrue(lines[0].startswith("You are an experienced news translator. Translate"))
        self.assertEqual(
            lines[2],
            "Style guidance, to follow wherever it does not contradict the instructions above: "
            "Use the agency's wire style.",
        )
        self.assertTrue(lines[3].startswith("Answer with the French translation"))

    async def test_the_character_limit_is_never_in_a_translation_prompt(self):
        prompt = render_system_prompt(
            AIActionType.TRANSLATION, output_field="body_html", count=1, max_characters=60, language="de"
        )

        self.assertNotIn("characters", prompt)

    async def test_a_translation_without_a_language_is_rejected(self):
        for language in (None, "", "   "):
            with self.subTest(language=language):
                with self.assertRaises(SuperdeskApiError) as context:
                    render_system_prompt(AIActionType.TRANSLATION, output_field="body_html", count=1, language=language)

                self.assertEqual(context.exception.status_code, 400)
                self.assertIn("language", context.exception.message)


class LanguageNameTestCase(IsolatedAsyncioTestCase):
    async def test_a_known_code_is_turned_into_its_name(self):
        self.assertEqual(language_name("de"), "German")
        self.assertEqual(language_name("EN"), "English")

    async def test_the_region_of_a_known_code_is_kept_next_to_its_name(self):
        self.assertEqual(language_name("pt-BR"), "Portuguese (BR)")
        self.assertEqual(language_name("fr_CA"), "French (CA)")

    async def test_anything_else_is_passed_through(self):
        self.assertEqual(language_name("Swahili"), "Swahili")
        self.assertEqual(language_name(" xx-YY "), "xx-YY")


class ParseTranslationTestCase(IsolatedAsyncioTestCase):
    async def test_the_whole_answer_is_the_translation_markup_and_lines_included(self):
        content = "<p>Der Rat tagte am Dienstag.</p>\n<p>Er stimmte über den Haushalt ab.</p>"

        self.assertEqual(parse_translation(content), content)

    async def test_a_code_fence_around_the_translation_is_dropped(self):
        content = "```html\n<p>Der Rat tagte am Dienstag.</p>\n```"

        self.assertEqual(parse_translation(content), "<p>Der Rat tagte am Dienstag.</p>")


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
