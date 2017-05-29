
import re
import bson
import superdesk
import superdesk.schema as schema

from copy import deepcopy
from superdesk.errors import SuperdeskApiError
from apps.auth import get_user_id
from superdesk import get_resource_service
from apps.templates.content_templates import remove_profile_from_templates
from apps.desks import remove_profile_from_desks
from eve.utils import ParsedRequest


CONTENT_TYPE_PRIVILEGE = 'content_type'


class DefaultSchema(schema.Schema):
    """Default schema."""

    #: keywords
    keywords = schema.ListField()

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
    'slugline': {'order': 0, 'sdWidth': 'full', 'enabled': True},
    'keywords': {'order': 1, 'sdWidth': 'full', 'enabled': False},
    'genre': {'order': 2, 'sdWidth': 'half', 'enabled': True},
    'anpa_take_key': {'order': 3, 'sdWidth': 'half', 'enabled': False},
    'place': {'order': 4, 'sdWidth': 'half', 'enabled': True},
    'priority': {'order': 5, 'sdWidth': 'quarter', 'enabled': True},
    'urgency': {'order': 6, 'sdWidth': 'quarter', 'enabled': True},
    'anpa_category': {'order': 7, 'sdWidth': 'full', 'enabled': True},
    'subject': {'order': 8, 'sdWidth': 'full', 'enabled': True},
    'company_codes': {'order': 9, 'sdWidth': 'full', 'enabled': False},
    'ednote': {'order': 10, 'sdWidth': 'full', 'enabled': True},
    'headline': {'order': 11, 'formatOptions': ['underline', 'anchor', 'bold', 'removeFormat'], 'enabled': True},
    'sms': {'order': 12, 'enabled': False},
    'abstract': {
        'order': 13,
        'formatOptions': ['bold', 'italic', 'underline', 'anchor', 'removeFormat'],
        'enabled': True
    },
    'byline': {'order': 14, 'enabled': True},
    'dateline': {'order': 15, 'enabled': True},
    'body_html': {
        'order': 16,
        'formatOptions': ['h2', 'bold', 'italic', 'underline', 'quote', 'anchor', 'embed', 'picture', 'removeFormat'],
        'cleanPastedHTML': False,
        'enabled': True
    },
    'footer': {'order': 17, 'enabled': False},
    'body_footer': {'order': 18, 'enabled': False},
    'sign_off': {'order': 19, 'enabled': True},
    'feature_media': {'enabled': True},
    'media_description': {'enabled': True},
}


class ContentTypesResource(superdesk.Resource):
    schema = {
        '_id': {
            'type': 'string',
            'iunique': True,
        },
        'label': {
            'type': 'string',
            'iunique': True,
        },
        'description': {
            'type': 'string',
        },
        'schema': {
            'type': 'dict'
        },
        'editor': {
            'type': 'dict'
        },
        'priority': {
            'type': 'integer',
            'default': 0,
        },
        'enabled': {
            'type': 'boolean',
            'default': False,
        },
        'is_used': {
            'type': 'boolean',
            'default': False,
        },
        'created_by': superdesk.Resource.rel('users', nullable=True),
        'updated_by': superdesk.Resource.rel('users', nullable=True),
    }

    item_url = r'regex("[\w,.:-]+")'

    privileges = {'POST': CONTENT_TYPE_PRIVILEGE,
                  'PATCH': CONTENT_TYPE_PRIVILEGE,
                  'DELETE': CONTENT_TYPE_PRIVILEGE}

    datasource = {
        'default_sort': [('priority', -1)],
    }


class ContentTypesService(superdesk.Service):
    def _set_updated_by(self, doc):
        doc['updated_by'] = get_user_id()

    def _set_created_by(self, doc):
        doc['created_by'] = get_user_id()

    def on_create(self, docs):
        for doc in docs:
            self._set_updated_by(doc)
            self._set_created_by(doc)

    def on_delete(self, doc):
        if doc.get('is_used'):
            raise SuperdeskApiError(status_code=202, payload={"is_used": True})
        remove_profile_from_templates(doc)
        remove_profile_from_desks(doc)

    def on_update(self, updates, original):
        self._validate_disable(updates, original)
        self._set_updated_by(updates)
        prepare_for_save_content_type(original, updates)
        self._update_template_fields(updates, original)

    def _validate_disable(self, updates, original):
        """
        Checks the templates and desks that are referencing the given
        content profile if the profile is being disabled
        """
        if 'enabled' in updates and updates.get('enabled') is False and original.get('enabled') is True:
            templates = list(superdesk.get_resource_service('content_templates').
                             get_templates_by_profile_id(original.get('_id')))

            if len(templates) > 0:
                template_names = ', '.join([t.get('template_name') for t in templates])
                raise SuperdeskApiError.badRequestError(
                    message='Cannot disable content profile as following templates are referencing: {}'.
                    format(template_names))

            req = ParsedRequest()
            all_desks = list(superdesk.get_resource_service('desks').get(req=req, lookup={}))
            profile_desks = [desk for desk in all_desks if
                             desk.get('default_content_profile') == str(original.get('_id'))]

            if len(profile_desks) > 0:
                profile_desk_names = ', '.join([d.get('name') for d in profile_desks])
                raise SuperdeskApiError.badRequestError(
                    message='Cannot disable content profile as following desks are referencing: {}'.
                    format(profile_desk_names))

    def _update_template_fields(self, updates, original):
        """
        Finds the templates that are referencing the given
        content profile an clears the disabled fields
        """
        templates = list(superdesk.get_resource_service('content_templates').
                         get_templates_by_profile_id(original.get('_id')))

        for template in templates:
            data = deepcopy(template.get('data', {}))
            schema = updates.get('schema', {})
            processed = False
            for field, params in schema.items():
                if not params or not params.get('enabled', True):
                    data.pop(field, None)
                    processed = True
            if processed:
                superdesk.get_resource_service('content_templates').patch(template.get('_id'), {'data': data})

    def find_one(self, req, **lookup):
        doc = super().find_one(req, **lookup)
        if doc and req and 'edit' in req.args:
            prepare_for_edit_content_type(doc)
        if doc:
            clean_doc(doc)
        return doc

    def set_used(self, profile_ids):
        """Set `is_used` flag for content profiles.

        :param profile_ids
        """
        query = {'_id': {'$in': list(profile_ids)}, 'is_used': {'$ne': True}}
        update = {'$set': {'is_used': True}}
        self.find_and_modify(query=query, update=update)

    def get_output_name(self, profile):
        try:
            _id = bson.ObjectId(profile)
            item = self.find_one(req=None, _id=_id) or {}
            return re.compile('[^0-9a-zA-Z_]').sub('', item.get('label', str(_id)))
        except bson.errors.InvalidId:
            return profile


def clean_doc(doc):
    clean_json(doc.get('schema', {}))
    clean_json(doc.get('editor', {}))


def clean_json(json):
    if not isinstance(json, dict):
        return
    for key in list(json.keys()):
        value = json[key]
        if value is None:
            del json[key]
        else:
            clean_json(value)


def prepare_for_edit_content_type(doc):
    clean_doc(doc)
    init_default(doc)
    editor = doc['editor']
    schema = doc['schema']
    fields_map, field_names = get_fields_map_and_names()
    init_custom(editor, schema, fields_map)
    expand_subject(editor, schema, fields_map)
    set_field_name(editor, field_names)


def get_allowed_list(schema):
    try:
        return schema['schema']['schema']['scheme']['allowed']
    except KeyError:
        return []


def get_mandatory_list(schema):
    return schema['mandatory_in_list']['scheme']


def get_fields_map_and_names():
    vocabularies = get_resource_service('vocabularies').find({'service': {'$exists': True}})
    fields_map = {}
    field_names = {}

    for vocabulary in vocabularies:
        fields_map[vocabulary.get('schema_field', vocabulary['_id'])] = vocabulary['_id']
        field_names[vocabulary['_id']] = vocabulary.get('display_name', vocabulary['_id'])

    return fields_map, field_names


def init_default(doc):
    editor = doc['editor'] = doc.get('editor', None)
    schema = doc['schema'] = doc.get('schema', None)
    if editor and schema:
        for field in DEFAULT_EDITOR:
            # add missing fields in editor with enabled = false
            if editor.get(field, None) is None:
                editor[field] = deepcopy(DEFAULT_EDITOR[field])
                editor[field]['enabled'] = False
                if schema.get(field, None) is None:
                    schema[field] = deepcopy(DEFAULT_SCHEMA[field])
            else:
                editor[field]['enabled'] = True
    else:
        doc['editor'] = deepcopy(DEFAULT_EDITOR)
        doc['schema'] = deepcopy(DEFAULT_SCHEMA)


def init_custom(editor, schema, fields_map):
    # process custom fields defined on vocabularies
    for old_field, field in fields_map.items():
        if field != old_field:
            if (editor.get(field, None)):
                editor[field]['enabled'] = True
            # custom storage for field, replace default editor with custom one
            replace_key(editor, old_field, field)
            replace_key(schema, old_field, field)
        else:
            # fields are stored in subject so add new custom editor
            schema[field] = {'type': 'list', 'required': False}
            if editor.get(field, None):
                editor[field]['enabled'] = True
            else:
                editor[field] = {'enabled': False}


def replace_key(dictionary, oldKey, newKey):
    if dictionary.get(oldKey, None):
        if not dictionary.get(newKey, None):
            dictionary[newKey] = deepcopy(dictionary[oldKey])
        del dictionary[oldKey]
    elif not dictionary.get(newKey, None):
        dictionary[newKey] = {}


def expand_subject(editor, schema, fields_map):
    subject = get_subject_name(fields_map)
    allowed = get_allowed_list(schema[subject])
    mandatory = get_mandatory_list(schema[subject])
    default_values = schema[subject].get('default', [])
    schema[subject]['schema'] = {}
    set_enabled_for_custom(editor, allowed, fields_map)
    set_required_for_custom(editor, schema, mandatory, fields_map)
    set_default_for_custom(schema, default_values, fields_map)


def set_enabled_for_custom(editor, allowed, fields_map):
    for field in allowed:
        editor[fields_map.get(field, field)]['enabled'] = True


def set_required_for_custom(editor, schema, mandatory, fields_map):
    for field, value in mandatory.items():
        if field == value or field == 'subject':
            editor[fields_map.get(field, field)]['required'] = value is not None
            schema[fields_map.get(field, field)]['required'] = value is not None


def set_default_for_custom(schema, default_values, fields_map):
    for old_field, field in fields_map.items():
        if (field == old_field or old_field == 'subject') and schema.get(field, None) is not None:
            default = []
            for value in default_values:
                if value.get('scheme', None) == field:
                    default.append(value)
            schema[field]['default'] = default


def get_subject_name(fields_map):
    return fields_map.get('subject', 'subject')


def set_field_name(editor, field_names):
    for (field, name) in field_names.items():
        editor[field]['field_name'] = name


def prepare_for_save_content_type(original, updates):
    editor = updates['editor'] = updates.get('editor', {})
    schema = updates['schema'] = updates.get('schema', {})
    original = deepcopy(original)
    prepare_for_edit_content_type(original)
    concatenate_dictionary(original['editor'], editor)
    concatenate_dictionary(original['schema'], schema)
    delete_disabled_fields(editor, schema)
    fields_map, _ = get_fields_map_and_names()
    clean_editor(editor)
    init_schema_for_custom_fields(schema, fields_map)
    compose_subject_schema(schema, fields_map)
    init_editor_required(editor, schema)
    rename_schema_for_custom_fields(schema, fields_map)


def concatenate_dictionary(source, destination):
    for key in source:
        if key not in destination:
            destination[key] = source[key]


def delete_disabled_fields(editor, schema):
    for field, value in editor.items():
        if value is None or not value.get('enabled', False):
            editor[field] = None
            schema[field] = None


def clean_editor(editor):
    valid_attributes = ['order', 'sdWidth', 'required', 'hideDate',
                        'formatOptions', 'editor3', 'default', 'cleanPastedHTML']
    for field_value in editor.values():
        if not field_value:
            continue
        for attribute in list(field_value.keys()):
            if attribute not in valid_attributes:
                del field_value[attribute]


def compose_subject_schema(schema, fields_map):
    mandatory = {}
    allowed = []
    default = []
    for old_field, field in fields_map.items():
        if (old_field == field or old_field == 'subject') and schema.get(field, None):
            allowed.append(field)
            if schema[field].get('required', False):
                mandatory[old_field] = field
            else:
                mandatory[old_field] = None
            if schema[field].get('default', None):
                default.extend(schema[field]['default'])
        else:
            mandatory[old_field] = None
    if allowed:
        init_subject_schema(schema, default, mandatory, allowed, fields_map)


def init_subject_schema(schema, default, mandatory, allowed, fields_map):
    subject = get_subject_name(fields_map)
    schema[subject] = deepcopy(DEFAULT_SCHEMA['subject'])
    schema[subject]['default'] = default
    schema[subject]['mandatory_in_list']['scheme'] = mandatory
    schema[subject]['schema']['schema']['scheme']['allowed'] = allowed
    schema[subject]['required'] = mandatory['subject'] is not None


def init_editor_required(editor, schema):
    for field in schema:
        if editor[field] is not None and schema[field] is not None and schema[field].get('required') is not None:
            editor[field]['required'] = schema[field]['required']
            if schema[field]['required']:
                if (schema[field].get('minlength', 0) or 0) == 0:
                    schema[field]['minlength'] = 1
            else:
                if (schema[field].get('minlength', 0) or 0) > 0:
                    schema[field]['minlength'] = 0
            schema[field]['nullable'] = not schema[field]['required']


def init_schema_for_custom_fields(schema, fields_map):
    for field in fields_map.values():
        if schema.get(field, None) and schema[field].get('default', None):
            list_values = schema[field]['default']
            for value in list_values:
                value['scheme'] = field


def rename_schema_for_custom_fields(schema, fields_map):
    for old_field, field in fields_map.items():
        if field in schema:
            if old_field != field:
                schema[old_field] = schema[field]
            del schema[field]


def is_enabled(field, schema):
    """Return true if field is enabled using given schema.

    :param field: field name
    :param schema: schema dict
    """
    return schema.get(field) or schema.get(field) == {} or field not in DEFAULT_SCHEMA


def apply_schema(item):
    """Return item without fields that should not be there given it's profile.

    :param item: item to apply schema to
    """
    try:
        profile = get_resource_service('content_types').find_one(req=None, _id=item['profile'])
        schema = profile['schema']
    except:
        schema = DEFAULT_SCHEMA
    return {key: val for key, val in item.items() if is_enabled(key, schema)}
