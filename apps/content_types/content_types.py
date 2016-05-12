
import superdesk

from apps.auth import get_user_id


CONTENT_TYPE_PRIVILEGE = 'content_type'


class ContentTypesResource(superdesk.Resource):
    schema = {
        '_id': {
            'type': 'string',
            'unique': True,
        },
        'label': {
            'type': 'string',
        },
        'description': {
            'type': 'string',
        },
        'schema': {
            'type': 'dict',
        },
        'editor': {
            'type': 'dict',
        },
        'priority': {
            'type': 'integer',
            'default': 0,
        },
        'enabled': {
            'type': 'boolean',
            'default': True,
        },
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

    def on_create(self, docs):
        for doc in docs:
            self._set_updated_by(doc)

    def on_update(self, updates, original):
        self._set_updated_by(updates)
