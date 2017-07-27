
import superdesk.schema as schema


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
    subject = schema.ListField(required=True, mandatory_in_list={'scheme': {}}, schema={
        'type': 'dict',
        'schema': {
            'name': {},
            'qcode': {},
            'scheme': {
                'type': 'string',
                'required': True,
                'nullable': True,
                'allowed': []
            },
            'service': {'nullable': True},
            'parent': {'nullable': True}
        }
    })

    #: company codes
    company_codes = schema.ListField()

    #: editorial note
    ednote = schema.StringField()

    #: headline
    headline = schema.StringField(maxlength=64)

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
    feature_media = schema.SchemaField()

    #: embedded media description
    media_description = schema.SchemaField()


DEFAULT_SCHEMA = dict(DefaultSchema)


DEFAULT_EDITOR = {
    'slugline': {'order': 1, 'sdWidth': 'full', 'enabled': True},
    'keywords': {'order': 2, 'sdWidth': 'full', 'enabled': False},
    'language': {'order': 3, 'sdWidth': 'half', 'enabled': False},
    'usageterms': {'order': 4, 'sdWidth': 'full', 'enabled': False},
    'genre': {'order': 5, 'sdWidth': 'half', 'enabled': True},
    'anpa_take_key': {'order': 6, 'sdWidth': 'half', 'enabled': False},
    'place': {'order': 7, 'sdWidth': 'half', 'enabled': True},
    'priority': {'order': 8, 'sdWidth': 'quarter', 'enabled': True},
    'urgency': {'order': 9, 'sdWidth': 'quarter', 'enabled': True},
    'anpa_category': {'order': 10, 'sdWidth': 'full', 'enabled': True},
    'subject': {'order': 11, 'sdWidth': 'full', 'enabled': True},
    'company_codes': {'order': 12, 'sdWidth': 'full', 'enabled': False},
    'ednote': {'order': 13, 'sdWidth': 'full', 'enabled': True},
    'headline': {'order': 14, 'formatOptions': ['underline', 'anchor', 'bold', 'removeFormat'], 'enabled': True},
    'sms': {'order': 15, 'enabled': False},
    'abstract': {
        'order': 16,
        'formatOptions': ['bold', 'italic', 'underline', 'anchor', 'removeFormat'],
        'enabled': True
    },
    'byline': {'order': 17, 'enabled': True},
    'dateline': {'order': 18, 'enabled': True},
    'body_html': {
        'order': 19,
        'formatOptions': ['h2', 'bold', 'italic', 'underline', 'quote', 'anchor', 'embed', 'picture', 'removeFormat'],
        'cleanPastedHTML': False,
        'enabled': True
    },
    'footer': {'order': 20, 'enabled': False},
    'body_footer': {'order': 21, 'enabled': False},
    'sign_off': {'order': 22, 'enabled': True},
    'feature_media': {'enabled': True},
    'media_description': {'enabled': True},
}
