import superdesk.schema as schema

from copy import deepcopy


class DefaultSchema(schema.Schema):
    """Default schema."""

    #: usageterms
    usageterms = schema.StringField()

    #: keywords
    keywords = schema.ListField()

    #: language
    language = schema.StringField()

    #: slugline
    slugline = schema.StringField(maxlength=24)

    #: item genre
    genre = schema.ListField()

    #: anpa take key
    anpa_take_key = schema.StringField()

    #: place where news happened
    place = schema.ListField()

    #: news item priority
    priority = schema.IntegerField()

    #: news item urgency
    urgency = schema.IntegerField()

    #: category
    anpa_category = schema.ListField()

    #: subject
    subject = schema.ListField(
        required=False,
        mandatory_in_list={"scheme": {}},
        schema={
            "type": "dict",
            "schema": {
                "name": {},
                "qcode": {},
                "scheme": {"type": "string", "required": True, "nullable": True, "allowed": []},
                "service": {"nullable": True},
                "parent": {"nullable": True},
            },
        },
    )

    #: company codes
    company_codes = schema.ListField()

    #: editorial note
    ednote = schema.StringField()

    #: authors
    authors = schema.ListField(
        schema={
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "parent": {"type": "string"},
                "role": {"type": "string"},
            },
        }
    )

    #: headline
    headline = schema.StringField(maxlength=64, required=True)

    #: sms version of an item
    sms = schema.StringField()

    #: item abstract
    abstract = schema.StringField(maxlength=160)

    #: byline
    byline = schema.StringField()

    #: dateline - info about where news was written
    dateline = schema.DictField()

    #: item content
    body_html = schema.StringField()

    #: item footer
    footer = schema.StringField()

    #: body footer
    body_footer = schema.StringField()

    #: item sign off info
    sign_off = schema.StringField()

    #: embedded media in the item
    feature_media = schema.MediaField()

    #: embedded media description
    media_description = schema.StringField()

    #: item attachments
    #: .. versionadded:: 1.29
    attachments = schema.ListField()

    relatedItems = {}


DEFAULT_SCHEMA = dict(DefaultSchema)

DEFAULT_MEDIA_SCHEMA = deepcopy(DEFAULT_SCHEMA)
DEFAULT_MEDIA_SCHEMA.pop("body_html")
DEFAULT_MEDIA_SCHEMA.pop("body_footer")
DEFAULT_MEDIA_SCHEMA["subject"]["required"] = False
DEFAULT_MEDIA_SCHEMA["headline"]["required"] = False


DEFAULT_EDITOR = {
    "slugline": {"order": 1, "sdWidth": "full", "enabled": True},
    "keywords": {"order": 2, "sdWidth": "full", "enabled": False},
    "language": {"order": 3, "sdWidth": "half", "enabled": False},
    "usageterms": {"order": 4, "sdWidth": "full", "enabled": False},
    "genre": {"order": 5, "sdWidth": "half", "enabled": True},
    "anpa_take_key": {"order": 6, "sdWidth": "half", "enabled": False},
    "place": {"order": 7, "sdWidth": "half", "enabled": True},
    "priority": {"order": 8, "sdWidth": "quarter", "enabled": True},
    "urgency": {"order": 9, "sdWidth": "quarter", "enabled": True},
    "anpa_category": {"order": 10, "sdWidth": "full", "enabled": True},
    "subject": {"order": 11, "sdWidth": "full", "enabled": True},
    "company_codes": {"order": 12, "sdWidth": "full", "enabled": False},
    "ednote": {"order": 13, "sdWidth": "full", "enabled": True},
    "authors": {"order": 14, "sdWidth": "full", "enabled": True},
    "headline": {"order": 15, "sdWidth": "full", "formatOptions": [], "enabled": True},
    "sms": {"order": 16, "enabled": False},
    "abstract": {
        "order": 17,
        "formatOptions": ["bold", "italic", "underline", "link"],
        "editor3": True,
        "enabled": True,
        "sdWidth": "full",
    },
    "byline": {"order": 18, "enabled": True, "sdWidth": "full"},
    "dateline": {"order": 19, "enabled": True, "sdWidth": "full"},
    "body_html": {
        "order": 20,
        "formatOptions": ["h2", "bold", "italic", "underline", "quote", "link", "embed", "media"],
        "cleanPastedHTML": False,
        "editor3": True,
        "enabled": True,
        "sdWidth": "full",
    },
    "footer": {"order": 21, "enabled": False},
    "body_footer": {"order": 22, "enabled": False},
    "sign_off": {"order": 23, "enabled": True, "sdWidth": "full"},
    "feature_media": {"enabled": True, "sdWidth": "full"},
    "media_description": {"enabled": True, "sdWidth": "full"},
    "attachments": {"enabled": False},
}

DEFAULT_MEDIA_EDITOR = deepcopy(DEFAULT_EDITOR)
DEFAULT_MEDIA_EDITOR.pop("body_html")
DEFAULT_MEDIA_EDITOR.pop("body_footer")

DEFAULT_SCHEMA_MAP = {
    "text": DEFAULT_SCHEMA,
    "audio": DEFAULT_MEDIA_SCHEMA,
    "video": DEFAULT_MEDIA_SCHEMA,
    "picture": DEFAULT_MEDIA_SCHEMA,
    "graphic": DEFAULT_MEDIA_SCHEMA,
    "composite": DEFAULT_MEDIA_SCHEMA,
}

DEFAULT_EDITOR_MAP = {
    "text": DEFAULT_EDITOR,
    "audio": DEFAULT_MEDIA_EDITOR,
    "video": DEFAULT_MEDIA_EDITOR,
    "picture": DEFAULT_MEDIA_EDITOR,
    "graphic": DEFAULT_MEDIA_EDITOR,
    "composite": DEFAULT_MEDIA_EDITOR,
}
