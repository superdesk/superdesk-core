# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import logging
import json

from flask import request, current_app as app
from eve.utils import config
from eve.methods.common import serialize_value

from superdesk import privilege
from superdesk.notification import push_notification
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.users import get_user_from_request
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError
from superdesk.default_schema import DEFAULT_SCHEMA, DEFAULT_EDITOR

logger = logging.getLogger(__name__)


privilege(name="vocabularies", label="Vocabularies Management",
          description="User can manage vocabularies' contents.")


# TODO(petr): add api to specify vocabulary schema
vocab_schema = {
    'crop_sizes': {
        'width': {'type': 'integer'},
        'height': {'type': 'integer'},
    }
}


class VocabulariesResource(Resource):
    schema = {
        '_id': {
            'type': 'string',
            'required': True,
            'unique': True,
            'regex': '^[a-zA-Z0-9-_]+$'
        },
        'display_name': {
            'type': 'string',
            'required': True
        },
        'helper_text': {
            'type': 'string',
            'maxlength': 120
        },
        'type': {
            'type': 'string',
            'required': True,
            'allowed': ['manageable', 'unmanageable'],
        },
        'items': {
            'type': 'list',
            'required': True
        },
        'single_value': {
            'type': 'boolean',
        },
        'schema_field': {
            'type': 'string',
            'required': False,
            'nullable': True
        },
        'dependent': {
            'type': 'boolean',
        },
        'service': {
            'type': 'dict',
        },
        'priority': {
            'type': 'integer'
        },
        'unique_field': {
            'type': 'string',
            'required': False,
            'nullable': True
        },
        'schema': {
            'type': 'dict'
        },
        'field_type': {
            'type': 'string',
            'nullable': True,
        },
        'field_options': {
            'type': 'dict',
        }
    }

    soft_delete = True
    item_url = 'regex("[-_\w]+")'
    item_methods = ['GET', 'PATCH', 'DELETE']
    resource_methods = ['GET', 'POST']
    privileges = {'PATCH': 'vocabularies', 'POST': 'vocabularies', 'DELETE': 'vocabularies'}
    mongo_indexes = {'field_type': [('field_type', 1)]}


class VocabulariesService(BaseService):

    system_keys = set(DEFAULT_SCHEMA.keys()).union(set(DEFAULT_EDITOR.keys()))

    def on_create(self, docs):
        for doc in docs:
            if doc.get('field_type') and doc['_id'] in self.system_keys:
                raise SuperdeskApiError(
                    message='{} is in use'.format(doc['_id']),
                    payload={'_id': {'conflict': 1}})

    def on_replace(self, document, original):
        document[app.config['LAST_UPDATED']] = utcnow()
        document[app.config['DATE_CREATED']] = original.get(app.config['DATE_CREATED'],
                                                            utcnow()) if original else utcnow()
        logger.info("updating vocabulary item: %s", document["_id"])

    def on_fetched(self, doc):
        """Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.

        It keeps it when requested for manageable vocabularies.
        """

        if request and hasattr(request, 'args') and request.args.get('where'):
            where_clause = json.loads(request.args.get('where'))
            if where_clause.get('type') == 'manageable':
                return doc

        for item in doc[config.ITEMS]:
            self._filter_inactive_vocabularies(item)
            self._cast_items(item)

    def on_fetched_item(self, doc):
        """
        Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.
        """
        self._filter_inactive_vocabularies(doc)
        self._cast_items(doc)

    def on_update(self, updates, original):
        """Checks the duplicates if a unique field is defined"""
        unique_field = original.get('unique_field')
        if unique_field:
            self._check_uniqueness(updates.get('items', []), unique_field)

    def on_updated(self, updates, original):
        """
        Overriding this to send notification about the replacement
        """
        self._send_notification(original)

    def on_replaced(self, document, original):
        """
        Overriding this to send notification about the replacement
        """
        self._send_notification(document)

    def on_delete(self, doc):
        """
        Overriding to validate vocabulary deletion
        """
        if 'field_type' not in doc:
            raise SuperdeskApiError.badRequestError('Default vocabularies cannot be deleted')

    def _check_uniqueness(self, items, unique_field):
        """Checks the uniqueness if a unique field is defined

        :param items: list of items to check for uniqueness
        :param unique_field: name of the unique field
        """
        unique_values = []
        for item in items:
            # compare only the active items
            if not item.get('is_active'):
                continue

            if not item.get(unique_field):
                raise SuperdeskApiError.badRequestError("{} cannot be empty".format(unique_field))

            unique_value = str(item.get(unique_field)).upper()

            if unique_value in unique_values:
                raise SuperdeskApiError.badRequestError("Value {} for field {} is not unique".
                                                        format(item.get(unique_field), unique_field))

            unique_values.append(unique_value)

    def _filter_inactive_vocabularies(self, item):
        vocs = item['items']
        active_vocs = ({k: voc[k] for k in voc.keys() if k != 'is_active'}
                       for voc in vocs if voc.get('is_active', True))

        item['items'] = list(active_vocs)

    def _cast_items(self, vocab):
        """Cast values in vocabulary items using predefined schema.

        :param vocab
        """
        schema = vocab_schema.get(vocab.get('_id'), {})
        for item in vocab.get('items', []):
            for field, field_schema in schema.items():
                if field in item:
                    item[field] = serialize_value(field_schema['type'], item[field])

    def _send_notification(self, updated_vocabulary):
        """
        Sends notification about the updated vocabulary to all the connected clients.
        """

        user = get_user_from_request()
        push_notification('vocabularies:updated', vocabulary=updated_vocabulary.get('display_name'),
                          user=str(user[config.ID_FIELD]) if user else None,
                          vocabulary_id=updated_vocabulary['_id'])

    def get_rightsinfo(self, item):
        rights_key = item.get('source', item.get('original_source', 'default'))
        all_rights = self.find_one(req=None, _id='rightsinfo')
        if not all_rights or not all_rights.get('items'):
            return {}
        try:
            all_rights['items'] = self.get_locale_vocabulary(all_rights.get('items'), item.get('language'))
            default_rights = next(info for info in all_rights['items'] if info['name'] == 'default')
        except StopIteration:
            default_rights = None
        try:
            rights = next(info for info in all_rights['items'] if info['name'] == rights_key)
        except StopIteration:
            rights = default_rights
        if rights:
            return {
                'copyrightholder': rights.get('copyrightHolder'),
                'copyrightnotice': rights.get('copyrightNotice'),
                'usageterms': rights.get('usageTerms'),
            }
        else:
            return {}

    def get_extra_fields(self):
        return list(self.get(req=None, lookup={'field_type': {'$exists': True, '$ne': None}}))

    def get_custom_vocabularies(self):
        return list(self.get(req=None, lookup={
            'field_type': None,
            'service': {'$exists': True},
        }))

    def get_locale_vocabulary(self, vocabulary, language):
        if not vocabulary or not language:
            return vocabulary
        locale_vocabulary = []
        for item in vocabulary:
            if 'translations' not in item:
                locale_vocabulary.append(item)
                continue
            new_item = item.copy()
            locale_vocabulary.append(new_item)
            for field, values in new_item.get('translations', {}).items():
                if field in new_item and language in values:
                    new_item[field] = values[language]
        return locale_vocabulary
