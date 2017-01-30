
import superdesk

from superdesk.errors import SuperdeskApiError
from apps.auth import get_user_id
from superdesk import get_resource_service
from copy import deepcopy

CONTENT_TYPE_PRIVILEGE = 'content_type'

DEFAULT_SCHEMA = {
    'slugline': {'maxlength': 24, 'type': 'string', 'required': False},
    'genre': {'type': 'list', 'required': False},
    'anpa_take_key': {'type': 'string', 'required': False},
    'place': {'type': 'list', 'required': False},
    'priority': {'type': 'integer', 'required': False},
    'urgency': {'type': 'integer', 'required': False},
    'anpa_category': {'type': 'list', 'required': False},
    'subject': {
        'type': 'list',
        'required': True,
        'mandatory_in_list': {'scheme': {}},
        'schema': {
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
        }
    },
    'company_codes': {'type': 'list', 'required': False},
    'ednote': {'type': 'string', 'required': False},
    'headline': {'maxlength': 64, 'type': 'string', 'required': False},
    'sms': {'type': 'string', 'required': False},
    'abstract': {'maxlength': 160, 'type': 'string', 'required': False},
    'byline': {'type': 'string', 'required': False},
    'dateline': {'type': 'dict', 'required': False},
    'body_html': {'type': 'string', 'required': False},
    'footer': {'type': 'string', 'required': False},
    'body_footer': {'type': 'string', 'required': False},
    'sign_off': {'type': 'string', 'required': False},
    'feature_media': {'type': 'picture', 'required': False},
    'media_description': {'required': False}
}

DEFAULT_EDITOR = {
    'slugline': {'order': 1, 'sdWidth': 'full', 'enabled': True},
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
    'feature_media': {'order': 20, 'enabled': False},
    'media_description': {'enabled': True},
}


class ContentTypesResource(superdesk.Resource):
    schema = {
        '_id': {
            'type': 'string',
            'unique': True,
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

    item_url = 'regex("[\w,.:-]+")'

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

    def on_update(self, updates, original):
        self._set_updated_by(updates)
        prepare_for_save_content_type(original, updates)

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
    fieldsMap = get_field_map()
    init_custom(editor, schema, fieldsMap)
    expand_subject(editor, schema, fieldsMap)
    set_field_name(editor, fieldsMap)


def get_allowed_list(schema):
    try:
        return schema['schema']['schema']['scheme']['allowed']
    except KeyError:
        return []


def get_mandatory_list(schema):
    return schema['mandatory_in_list']['scheme']


def get_field_map():
    vocabularies = get_resource_service('vocabularies').find({'service': {'$exists': True}})
    return {
        vocabulary.get('schema_field', vocabulary['_id']): vocabulary['_id']
        for vocabulary in vocabularies
    }


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


def init_custom(editor, schema, fieldsMap):
    # process custom fields defined on vocabularies
    for old_field, field in fieldsMap.items():
        if field != old_field:
            if (editor.get(field, None)):
                editor[field]['enabled'] = True
            # custom storage for field, replace default editor with custom one
            replaceKey(editor, old_field, field)
            replaceKey(schema, old_field, field)
        else:
            # fields are stored in subject so add new custom editor
            schema[field] = {'type': 'list', 'required': False}
            if editor.get(field, None):
                editor[field]['enabled'] = True
            else:
                editor[field] = {'enabled': False}


def replaceKey(dictionary, oldKey, newKey):
    if dictionary.get(oldKey, None):
        if not dictionary.get(newKey, None):
            dictionary[newKey] = deepcopy(dictionary[oldKey])
        del dictionary[oldKey]
    elif not dictionary.get(newKey, None):
        dictionary[newKey] = {}


def expand_subject(editor, schema, fieldsMap):
    subject = getSubjectName(fieldsMap)
    allowed = get_allowed_list(schema[subject])
    mandatory = get_mandatory_list(schema[subject])
    schema[subject]['schema'] = {}
    set_enabled_for_custom(editor, allowed, fieldsMap)
    set_required_for_custom(editor, schema, mandatory, fieldsMap)


def set_enabled_for_custom(editor, allowed, fieldsMap):
    for field in allowed:
        editor[fieldsMap.get(field, field)]['enabled'] = True


def set_required_for_custom(editor, schema, mandatory, fieldsMap):
    for field, value in mandatory.items():
        if field == value or field == 'subject':
            editor[fieldsMap.get(field, field)]['required'] = value is not None
            schema[fieldsMap.get(field, field)]['required'] = value is not None


def getSubjectName(fieldsMap):
    return fieldsMap.get('subject', 'subject')


def set_field_name(editor, fieldsMap):
    for (old_field, field) in fieldsMap.items():
        editor[field]['field_name'] = old_field


def prepare_for_save_content_type(original, updates):
    editor = updates['editor'] = updates.get('editor', {})
    schema = updates['schema'] = updates.get('schema', {})
    original = deepcopy(original)
    prepare_for_edit_content_type(original)
    concatenate_dictionary(original['editor'], editor)
    concatenate_dictionary(original['schema'], schema)
    delete_disabled_fields(editor, schema)
    fieldMap = get_field_map()
    clean_editor(editor)
    init_schema_for_custom_fields(schema, fieldMap)
    compose_subject_schema(schema, fieldMap)
    init_editor_required(editor, schema)
    rename_schema_for_custom_fields(schema, fieldMap)


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


def compose_subject_schema(schema, fieldMap):
    mandatory = {}
    allowed = []
    for old_field, field in fieldMap.items():
        if (old_field == field or old_field == 'subject') and schema.get(field, None):
            allowed.append(field)
            if schema[field].get('required', False):
                mandatory[old_field] = field
            else:
                mandatory[old_field] = None
        else:
            mandatory[old_field] = None
    if allowed:
        init_subject_schema(schema, mandatory, allowed, fieldMap)


def init_subject_schema(schema, mandatory, allowed, fieldMap):
    subject = getSubjectName(fieldMap)
    schema[subject] = deepcopy(DEFAULT_SCHEMA['subject'])
    schema[subject]['mandatory_in_list']['scheme'] = mandatory
    schema[subject]['schema']['schema']['scheme']['allowed'] = allowed
    schema[subject]['required'] = mandatory['subject'] is not None


def init_editor_required(editor, schema):
    for field in schema:
        if editor[field] is not None and schema[field] is not None and schema[field].get('required') is not None:
            editor[field]['required'] = schema[field]['required']
            schema[field]['minlength'] = 1 if schema[field]['required'] else 0


def init_schema_for_custom_fields(schema, fieldMap):
    for field in fieldMap.values():
        if schema.get(field, None) and schema[field].get('default', None):
            list_values = schema[field]['default']
            for value in list_values:
                value['scheme'] = field


def rename_schema_for_custom_fields(schema, fieldMap):
    for old_field, field in fieldMap.items():
        if field in schema:
            if old_field != field:
                schema[old_field] = schema[field]
            del schema[field]
