"""
Avoid using default `language` field for text indexes
as it would throw an error when saving document with
unsupported language.

So instead we should define indexes with custom language
field (via `language_override`) and only set it when it's supported.
"""

_TEXT_MONGO_LANGUAGE = "_mongo_language"

# https://docs.mongodb.com/manual/reference/text-search-languages/#text-search-languages
_TEXT_SUPPORTED_LANGUAGES = {
    "da",
    "nl",
    "en",
    "fi",
    "fr",
    "de",
    "hu",
    "it",
    "nb",
    "pt",
    "ro",
    "ru",
    "es",
    "sv",
    "tr",
}

TEXT_INDEX_OPTIONS = {
    "background": True,
    "language_override": _TEXT_MONGO_LANGUAGE,
}


def set_mongo_lang(doc):
    """Mongo only supports certain languages and won't story document with unsupported one."""
    if doc.get("language"):
        mongo_lang = get_mongo_language(doc["language"])
        if mongo_lang:
            doc[_TEXT_MONGO_LANGUAGE] = mongo_lang


def get_mongo_language(lang):
    if not lang:
        return
    lang = lang.split("-")[0].split("_")[0]
    return lang if lang in _TEXT_SUPPORTED_LANGUAGES else None
