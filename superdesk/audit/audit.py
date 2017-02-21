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
from superdesk.resource import Resource
from superdesk.services import BaseService

log = logging.getLogger(__name__)


class AuditResource(Resource):
    endpoint_name = 'audit'
    resource_methods = ['GET']
    item_methods = ['GET']
    schema = {
        'resource': {'type': 'string'},
        'action': {'type': 'string'},
        'extra': {'type': 'dict'},
        'user': Resource.rel('users', False)
    }
    exclude = {endpoint_name, 'activity', 'dictionaries', 'macros', 'archive_history'}


class AuditService(BaseService):
    def on_generic_inserted(self, resource, docs):
        if resource in AuditResource.exclude:
            return

        user = getattr(g, 'user', None)
        if not user:
            if resource == 'auth':
                user_id = docs[0].get('user')
            else:
                return
        else:
            user_id = user.get('_id')

        if not len(docs):
            return

        audit = {
            'user': user_id,
            'resource': resource,
            'action': 'created',
            'extra': docs[0]
        }

        self.post([audit])

    def on_generic_updated(self, resource, doc, original):
        if resource in AuditResource.exclude:
            return

        user = getattr(g, 'user', None)
        if not user:
            return

        audit = {
            'user': user.get('_id'),
            'resource': resource,
            'action': 'updated',
            'extra': doc
        }
        if '_id' not in doc:
            audit['extra']['_id'] = original.get('_id', None)
        self.post([audit])

    def on_generic_deleted(self, resource, doc):
        if resource in AuditResource.exclude:
            return

        user = getattr(g, 'user', None)
        if not user:
            return

        audit = {
            'user': user.get('_id'),
            'resource': resource,
            'action': 'deleted',
            'extra': doc
        }
        self.post([audit])
