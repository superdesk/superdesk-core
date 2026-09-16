"""Prompt assembly and answer parsing for the supported AI action types.

The templates are plain strings formatted with :meth:`str.format`, so any literal brace in one of
them has to be doubled. ``JSON_CONTRACT`` contains the answer shape and is never formatted, which
is why it can hold real braces.
"""

import json
import re
from typing import Any, Mapping

from quart_babel import gettext

from .errors import AIErrorKind, AIProviderError, NotSupportedError
from .models import AIActionType

SYSTEM_TEMPLATES: dict[AIActionType, str] = {
    AIActionType.SUGGESTION: (
        "You are an experienced news editor. Write {count} alternative versions of the "
        "'{output_field}' of the article the user sends."
    ),
    AIActionType.SUMMARY: (
        "You are an experienced news editor. Write a summary of the article the user sends, "
        "to be used as its '{output_field}'."
    ),
}

#: Action types the run flow can build a prompt for, the rest are rejected as not supported
SUPPORTED_ACTION_TYPES = frozenset(SYSTEM_TEMPLATES)

FACTS_INSTRUCTION = "Use only the facts of the article the user sends, do not add any of your own."

MAX_CHARACTERS_INSTRUCTION = "Keep every version under {max_characters} characters."

LANGUAGE_INSTRUCTION = "Write every version in {language}."

JSON_CONTRACT = (
    'Answer with a JSON object and nothing else, of the form {"suggestions": ["first", "second"]}, '
    "with one entry per version and no formatting inside the entries."
)

# Bullet or numbered list marker at the start of a line, stripped when an answer has to be read
# line by line because the provider ignored the JSON contract
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s*")

# Markdown code fence around a whole answer, which several models add even in JSON mode
_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n?|\n?\s*```\s*$")

# Opening and closing quote of every pair a provider may wrap a single answer in, straight and
# curly. Only used on answers that did not follow the JSON contract.
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"))


def unsupported_action_type(action_type: AIActionType) -> NotSupportedError:
    """Build the error to answer a request for an action type that has no prompt template"""

    return NotSupportedError(
        gettext("AI action type '{action_type}' is not supported yet").format(action_type=action_type.value)
    )


def render_system_prompt(
    action_type: AIActionType,
    output_field: str,
    count: int,
    max_characters: int | None = None,
    language: str | None = None,
    system_prompt: str | None = None,
) -> str:
    """Build the system message for one run of an action

    :param action_type: Type of the action, picks the template
    :param output_field: Name of the item field the answers are written to, named in the prompt
    :param count: Number of versions to ask for
    :param max_characters: Optional length the answers should stay under
    :param language: Optional language to answer in, left out of the prompt when not known
    :param system_prompt: Optional replacement for the template of the action type. The instructions
        that follow it are always appended, so a custom prompt cannot drop the answer format.
    :raises NotSupportedError: If the action type has no template
    """

    template = SYSTEM_TEMPLATES.get(action_type)
    if template is None:
        raise unsupported_action_type(action_type)

    parts = [
        system_prompt or template.format(count=count, output_field=output_field),
        FACTS_INSTRUCTION,
    ]

    if max_characters is not None:
        parts.append(MAX_CHARACTERS_INSTRUCTION.format(max_characters=max_characters))
    if language:
        parts.append(LANGUAGE_INSTRUCTION.format(language=language))

    parts.append(JSON_CONTRACT)

    return "\n".join(parts)


def render_user_message(texts: Mapping[str, str]) -> str:
    """Build the user message from the text of each input field

    A single field is sent on its own, so the provider is not told a field name it does not need.
    Several fields are each prefixed with their name, so the provider can tell them apart.
    """

    if len(texts) == 1:
        return next(iter(texts.values()))

    return "\n\n".join(f"{name}:\n{text}" for name, text in texts.items())


def parse_suggestions(content: str, count: int) -> list[str]:
    """Read the answers out of a completion, at most ``count`` of them

    The JSON contract is tried first. A body that is not JSON at all is read one answer per line.
    A body that is JSON of another shape is only read when that shape leaves no doubt which part
    of it holds the answers.

    :raises AIProviderError: If the body is JSON no answers can be read out of
    """

    suggestions = _parse_json_suggestions(content)
    if suggestions is None:
        suggestions = _parse_line_suggestions(content)

    return suggestions[:count]


def _parse_json_suggestions(content: str) -> list[str] | None:
    """Read the answers from a JSON body, ``None`` when the body is not a JSON object or array

    :raises AIProviderError: If the body is a JSON object or array that holds no readable answers
    """

    try:
        data: Any = json.loads(_strip_code_fence(content))
    except ValueError:
        return None

    # A bare JSON string or number is a one line answer that happens to be valid JSON, so it is
    # left to the line parser instead of being read as a structure
    if not isinstance(data, (dict, list)):
        return None

    if isinstance(data, dict) and isinstance(data.get("suggestions"), list):
        return _texts(data["suggestions"])

    suggestions = _recover_suggestions(data)
    if suggestions is None:
        raise AIProviderError(
            AIErrorKind.INVALID_RESPONSE,
            gettext("The AI provider answered with JSON that holds no suggestions"),
        )

    return suggestions


def _recover_suggestions(data: Any) -> list[str] | None:
    """Read the answers out of a JSON shape other than the contract, ``None`` when it is ambiguous

    A list of strings is preferred over a lone string value, so an object that pairs the answers
    with a single label is still read as its list.
    """

    if isinstance(data, list):
        return _texts(data) or None

    for value in data.values():
        if isinstance(value, list):
            texts = _texts(value)
            if texts:
                return texts

    strings = _texts(data.values())

    return strings if len(strings) == 1 else None


def _parse_line_suggestions(content: str) -> list[str]:
    """Read one answer per line, keeping only the marked lines once any line carries a marker

    A provider that ignores the JSON contract usually introduces its list ("Here are 3 headlines:")
    and may close it with a remark. Those lines are prose about the answers, not answers.
    """

    lines = [line for line in _strip_code_fence(content).splitlines() if line.strip()]
    marked = [line for line in lines if _LIST_MARKER_RE.match(line)]

    return [text for text in (_clean_line(_LIST_MARKER_RE.sub("", line)) for line in (marked or lines)) if text]


def _texts(entries: Any) -> list[str]:
    return [text for text in (entry.strip() for entry in entries if isinstance(entry, str)) if text]


def _strip_code_fence(content: str) -> str:
    return _CODE_FENCE_RE.sub("", content).strip()


def _clean_line(text: str) -> str:
    """Trim a line, dropping one pair of quotes when it wraps the whole of the line

    Answers that follow the JSON contract are never trimmed this way: a provider writing prose
    quotes its answers, a provider filling in a JSON string does not, so a quote inside a JSON
    entry is always part of the answer.
    """

    text = text.strip()

    for opening, closing in _QUOTE_PAIRS:
        if len(text) > 1 and text.startswith(opening) and text.endswith(closing):
            inner = text[1:-1]
            # More quotes of the same kind inside mean the line quotes someone, and the outer pair
            # belongs to the answer rather than wrapping it
            if opening not in inner and closing not in inner:
                return inner.strip()

    return text
