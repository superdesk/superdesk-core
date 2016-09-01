
import superdesk

from superdesk.errors import SuperdeskApiError
from apps.auth import get_user_id
from superdesk import get_resource_service
from copy import deepcopy

CONTENT_TYPE_PRIVILEGE = 'content_type'

DEFAULT_SCHEMA = {
    'slugline': {'maxlength': 24, 'type': 'string'},
    'genre': {'type': 'list'},
    'anpa_take_key': {},
    'place': {'type': 'list'},
    'priority': {},
    'anpa_category': {'type': 'list'},
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
                    'allowed': ['subject']
                },
                'service': {'nullable': True},
                'parent': {'nullable': True}
            }
        }
    },
    'company_codes': {'type': 'list'},
    'ednote': {},
    'headline': {'maxlength': 64, 'type': 'string'},
    'sms': None,
    'abstract': {'maxlength': 160, 'type': 'string'},
    'byline': {'type': 'string'},
    'dateline': {'type': 'dict'},
    'body_html': {},
    'footer': None,
    'body_footer': None,
    'sign_off': {'type': 'string'},
    'media': {},
    'media_description': {}
}

DEFAULT_EDITOR = {
    'slugline': {'order': 1, 'sdWidth': 'full', 'enabled': True},
    'genre': {'order': 2, 'sdWidth': 'half', 'enabled': True},
    'anpa_take_key': {'order': 3, 'sdWidth': 'half', 'enabled': False},
    'place': {'order': 4, 'sdWidth': 'half', 'enabled': True},
    'priority': {'order': 5, 'sdWidth': 'quarter', 'enabled': True},
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
        'enabled': True
    },
    'footer': {'order': 17, 'enabled': False},
    'body_footer': {'order': 18, 'enabled': False},
    'sign_off': {'order': 19, 'enabled': True},
    'media': {'enabled': True},
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

    def get_allowed_list(self, schema):
        return schema['subject']['schema']['schema']['scheme']['allowed']

    def extend_content_type(self, doc):
        # set the editor/schema definition if they are not set
        editor = doc['editor'] = doc.get('editor', None)
        schema = doc['schema'] = doc.get('schema', None)
        default = False

        if editor and schema:
            for field in DEFAULT_EDITOR:
                # add missing fields in editor with enabled = false
                if field not in editor:
                    editor[field] = deepcopy(DEFAULT_EDITOR[field])
                    editor[field]['enabled'] = False
                    schema[field] = deepcopy(DEFAULT_SCHEMA[field])
        else:
            editor = doc['editor'] = deepcopy(DEFAULT_EDITOR)
            schema = doc['schema'] = deepcopy(DEFAULT_SCHEMA)
            default = True

        # process custom fields defined on vocabularies
        vocabularies = get_resource_service('vocabularies').find({'service': {'$exists': True}})
        for vocabulary in vocabularies:
            field = vocabulary['_id']
            if 'schema_field' in vocabulary:
                # custom storage for field, replace default editor with custom one
                old_field = vocabulary['schema_field']
                if old_field in editor:
                    if field not in editor:
                        # if not set the editor for field, set it
                        editor[field] = deepcopy(editor[old_field])
                        if not default:
                            editor[field]['enabled'] = False
                    del editor[old_field]
                if old_field == 'subject':
                    # if subject is custom replace in allowed subject with the new custom name
                    allowed_list = self.get_allowed_list(schema)
                    allowed_list.remove(old_field)
                    allowed_list.append(field)
                if old_field not in schema:
                    schema[old_field] = {}
            elif field not in editor:
                # fields are stored in subject so add new custom editor and add it to allowed in subject
                editor[field] = {'enabled': default}
                allowed_list = self.get_allowed_list(schema)
                allowed_list.append(field)

    def on_create(self, docs):
        for doc in docs:
            self._set_updated_by(doc)
            self._set_created_by(doc)

    def on_delete(self, doc):
        if doc.get('is_used'):
            raise SuperdeskApiError(status_code=202, payload={"is_used": True})

    def on_update(self, updates, original):
        self._set_updated_by(updates)

    def find_one(self, req, **lookup):
        doc = super().find_one(req, **lookup)
        if doc and req and 'edit' in req.args:
            self.extend_content_type(doc)
        return doc

    def set_used(self, profile_ids):
        """Set `is_used` flag for content profiles.

        :param profile_ids
        """
        query = {'_id': {'$in': list(profile_ids)}, 'is_used': {'$ne': True}}
        update = {'$set': {'is_used': True}}
        self.find_and_modify(query=query, update=update)
