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

from eve.utils import config
from flask import g, current_app as app

import superdesk
from superdesk import get_resource_service
from superdesk.activity import ACTIVITY_CREATE, ACTIVITY_EVENT, ACTIVITY_UPDATE, notify_and_add_activity, \
    ACTIVITY_DELETE
from superdesk.errors import SuperdeskApiError
from superdesk.io import allowed_feeding_services, allowed_feed_parsers
from superdesk.metadata.item import CONTENT_STATE, content_type
from superdesk.notification import push_notification
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.utc import utcnow
from superdesk.utils import required_string

logger = logging.getLogger(__name__)


class IngestProviderResource(Resource):

    def __init__(self, endpoint_name, app, service, endpoint_schema=None):
        self.schema = {
            'name': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'iunique': True
            },
            'source': required_string,
            'feeding_service': {
                'type': 'string',
                'required': True,
                'allowed': allowed_feeding_services
            },
            'feed_parser': {
                'type': 'string',
                'nullable': True,
                'allowed': allowed_feed_parsers
            },
            'content_types': {
                'type': 'list',
                'default': content_type,
                'allowed': content_type
            },
            'content_expiry': {
                'type': 'integer',
                'default': app.config['INGEST_EXPIRY_MINUTES']
            },
            'config': {
                'type': 'dict'
            },
            'ingested_count': {
                'type': 'integer'
            },
            'accepted_count': {
                'type': 'integer'
            },
            'token': {
                'type': 'dict'
            },
            'is_closed': {
                'type': 'boolean',
                'default': False
            },
            'update_schedule': {
                'type': 'dict',
                'schema': {
                    'hours': {'type': 'integer'},
                    'minutes': {'type': 'integer', 'default': 5},
                    'seconds': {'type': 'integer'},
                }
            },
            'idle_time': {
                'type': 'dict',
                'schema': {
                    'hours': {'type': 'integer'},
                    'minutes': {'type': 'integer'},
                }
            },
            'last_updated': {'type': 'datetime'},
            'last_item_update': {'type': 'datetime'},
            'rule_set': Resource.rel('rule_sets', nullable=True),
            'notifications': {
                'type': 'dict',
                'schema': {
                    'on_update': {'type': 'boolean', 'default': True},
                    'on_close': {'type': 'boolean', 'default': True},
                    'on_open': {'type': 'boolean', 'default': True},
                    'on_error': {'type': 'boolean', 'default': True}
                }
            },
            'routing_scheme': Resource.rel('routing_schemes', nullable=True),
            'last_closed': {
                'type': 'dict',
                'schema': {
                    'closed_at': {'type': 'datetime'},
                    'closed_by': Resource.rel('users', nullable=True),
                    'message': {'type': 'string'}
                }
            },
            'last_opened': {
                'type': 'dict',
                'schema': {
                    'opened_at': {'type': 'datetime'},
                    'opened_by': Resource.rel('users', nullable=True)
                }
            },
            'critical_errors': {
                'type': 'dict',
                'valueschema': {
                    'type': 'boolean'
                }
            },
        }

        self.item_methods = ['GET', 'PATCH', 'DELETE']
        self.privileges = {'POST': 'ingest_providers', 'PATCH': 'ingest_providers', 'DELETE': 'ingest_providers'}
        self.etag_ignore_fields = ['last_updated', 'last_item_update', 'last_closed', 'last_opened']

        super().__init__(endpoint_name, app, service, endpoint_schema=endpoint_schema)


class IngestProviderService(BaseService):
    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource=datasource, backend=backend)
        self.user_service = get_resource_service('users')

    def _set_provider_status(self, doc, message=''):
        user = getattr(g, 'user', None)
        if doc.get('is_closed', True):
            doc['last_closed'] = doc.get('last_closed', {})
            doc['last_closed']['closed_at'] = utcnow()
            doc['last_closed']['closed_by'] = user['_id'] if user else None
            doc['last_closed']['message'] = message
        else:
            doc['last_opened'] = doc.get('last_opened', {})
            doc['last_opened']['opened_at'] = utcnow()
            doc['last_opened']['opened_by'] = user['_id'] if user else None

    def on_create(self, docs):
        for doc in docs:
            if doc.get('content_expiry', 0) == 0:
                doc['content_expiry'] = app.config['INGEST_EXPIRY_MINUTES']
                self._set_provider_status(doc, doc.get('last_closed', {}).get('message', ''))

    def on_created(self, docs):
        for doc in docs:
            notify_and_add_activity(ACTIVITY_CREATE, 'Created Ingest Channel {{name}}',
                                    self.datasource, item=None,
                                    user_list=self.user_service.get_users_by_user_type('administrator'),
                                    name=doc.get('name'), provider_id=doc.get('_id'))
            push_notification('ingest_provider:create', provider_id=str(doc.get('_id')))
        logger.info("Created Ingest Channel. Data:{}".format(docs))

    def on_update(self, updates, original):
        if updates.get('content_expiry') == 0:
            updates['content_expiry'] = app.config['INGEST_EXPIRY_MINUTES']
        if 'is_closed' in updates and original.get('is_closed', False) != updates.get('is_closed'):
            self._set_provider_status(updates, updates.get('last_closed', {}).get('message', ''))

    def on_updated(self, updates, original):
        do_notification = updates.get('notifications', {})\
            .get('on_update', original.get('notifications', {}).get('on_update', True))
        notify_and_add_activity(ACTIVITY_UPDATE, 'updated Ingest Channel {{name}}',
                                self.datasource, item=None,
                                user_list=self.user_service.get_users_by_user_type('administrator')
                                if do_notification else None,
                                name=updates.get('name', original.get('name')),
                                provider_id=original.get('_id'))

        if updates.get('is_closed', False) != original.get('is_closed', False):
            status = ''
            do_notification = False

            if updates.get('is_closed'):
                status = 'closed'
                do_notification = updates.get('notifications', {}). \
                    get('on_close', original.get('notifications', {}).get('on_close', True))
            elif not updates.get('is_closed'):
                status = 'opened'
                do_notification = updates.get('notifications', {}). \
                    get('on_open', original.get('notifications', {}).get('on_open', True))

            notify_and_add_activity(ACTIVITY_EVENT, '{{status}} Ingest Channel {{name}}',
                                    self.datasource, item=None,
                                    user_list=self.user_service.get_users_by_user_type('administrator')
                                    if do_notification else None,
                                    name=updates.get('name', original.get('name')),
                                    status=status, provider_id=original.get('_id'))

        push_notification('ingest_provider:update', provider_id=str(original.get('_id')))
        logger.info("Updated Ingest Channel. Data: {}".format(updates))

    def on_delete(self, doc):
        """
        Overriding to check if the Ingest Source which has received item being deleted.
        """

        if doc.get('last_item_update'):
            raise SuperdeskApiError.forbiddenError("Deleting an Ingest Source after receiving items is prohibited.")

    def on_deleted(self, doc):
        """
        Overriding to send notification and record activity about channel deletion.
        """
        notify_and_add_activity(ACTIVITY_DELETE, 'Deleted Ingest Channel {{name}}',
                                self.datasource, item=None,
                                user_list=self.user_service.get_users_by_user_type('administrator'),
                                name=doc.get('name'), provider_id=doc.get(config.ID_FIELD))
        push_notification('ingest_provider:delete', provider_id=str(doc.get(config.ID_FIELD)))
        get_resource_service('sequences').delete(lookup={
            'key': 'ingest_providers_{_id}'.format(_id=doc[config.ID_FIELD])
        })
        logger.info("Deleted Ingest Channel. Data:{}".format(doc))


superdesk.workflow_state(CONTENT_STATE.INGESTED)
superdesk.workflow_action(name='ingest')
