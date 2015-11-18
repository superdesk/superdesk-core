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

from superdesk import privilege
from superdesk.notification import push_notification
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.users import get_user_from_request
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


privilege(name="vocabularies", label="Vocabularies Management",
          description="User can manage vocabularies' contents.")


class VocabulariesResource(Resource):
    schema = {
        '_id': {
            'type': 'string',
            'required': True,
            'unique': True
        },
        'display_name': {
            'type': 'string',
            'required': True
        },
        'type': {
            'type': 'string',
            'required': True,
            'allowed': ['manageable', 'unmanageable']
        },
        'items': {
            'type': 'list',
            'required': True
        }
    }

    item_url = 'regex("[\w]+")'
    item_methods = ['GET', 'PATCH']
    resource_methods = ['GET']
    privileges = {'PATCH': 'vocabularies', }


class VocabulariesService(BaseService):
    def on_replace(self, document, original):
        document[app.config['LAST_UPDATED']] = utcnow()
        document[app.config['DATE_CREATED']] = original[app.config['DATE_CREATED']] if original else utcnow()
        logger.info("updating vocabulary", document["_id"])

    def on_fetched(self, doc):
        """
        Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response if the
        request wasn't for manageable vocabularies.
        """

        if request and hasattr(request, 'args') and request.args.get('where'):
            where_clause = json.loads(request.args.get('where'))
            if where_clause.get('type') == 'manageable':
                return doc

        for item in doc[config.ITEMS]:
            self._filter_inactive_vocabularies(item)

    def on_fetched_item(self, doc):
        """
        Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.
        """

        self._filter_inactive_vocabularies(doc)

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

    def _filter_inactive_vocabularies(self, item):
        vocs = item['items']
        active_vocs = ({k: voc[k] for k in voc.keys() if k != 'is_active'}
                       for voc in vocs if voc.get('is_active', True))

        item['items'] = list(active_vocs)

    def _send_notification(self, updated_vocabulary):
        """
        Sends notification about the updated vocabulary to all the connected clients.
        """

        user = get_user_from_request()
        push_notification('vocabularies:updated', vocabulary=updated_vocabulary.get('display_name'),
                          user=str(user[config.ID_FIELD]) if user else None)
