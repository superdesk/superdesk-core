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
from flask import g
from eve.utils import config
from copy import deepcopy
from superdesk.resource import Resource
from superdesk.services import BaseService
from apps.archive.common import ITEM_UPDATE

log = logging.getLogger(__name__)

fields_to_remove = ['_id', '_etag', 'versioncreator', 'originalcreator', 'versioncreated',
                    '_current_version', 'version', '_updated', 'lock_session', 'lock_user', 'lock_time', 'lock_action',
                    'force_unlock', '_created', 'guid', 'family_id', 'firstcreated', 'original_creator']


class ArchiveHistoryResource(Resource):
    endpoint_name = 'archive_history'
    resource_methods = ['GET']
    item_methods = ['GET']
    schema = {
        'item_id': {'type': 'string'},
        'user_id': Resource.rel('users', True),
        'operation': {'type': 'string'},
        'update': {'type': 'dict', 'nullable': True},
        'version': {'type': 'integer'}
    }


class ArchiveHistoryService(BaseService):

    def on_item_updated(self, updates, original, operation=None):
        item = deepcopy(original)
        if updates:
            item.update(updates)
        self._save_history(item, updates, operation or ITEM_UPDATE)

    def on_item_deleted(self, doc):
        lookup = {'item_id': doc[config.ID_FIELD]}
        self.delete(lookup=lookup)

    def get_user_id(self, item):
        user = getattr(g, 'user', None)
        if user:
            return user.get('_id')

    def _save_history(self, item, update, operation):
        history = {
            'item_id': item[config.ID_FIELD],
            'user_id': self.get_user_id(item),
            'operation': operation,
            'update': self._remove_unwanted_fields(update, item),
            'version': item.get(config.VERSION, 1)
        }

        self.post([history])

    def _remove_unwanted_fields(self, update, original):
        if update:
            update_copy = deepcopy(update)
            for field in fields_to_remove:
                update_copy.pop(field, None)

            if original.get('sms_message') == update_copy.get('sms_message'):
                update_copy.pop('sms_message', None)

            return update_copy
