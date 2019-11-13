# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import datetime
import logging

from bson.objectid import ObjectId
from flask import g

import superdesk
from superdesk import get_resource_service
from superdesk.emails import send_activity_emails
from superdesk.errors import SuperdeskApiError, add_notifier
from superdesk.notification import push_notification
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.utc import utcnow
from eve.utils import ParsedRequest
from superdesk.metadata.item import PUBLISH_STATES
import json

log = logging.getLogger(__name__)


def init_app(app):

    endpoint_name = 'activity'
    service = ActivityService(endpoint_name, backend=superdesk.get_backend())
    ActivityResource(endpoint_name, app=app, service=service)

    # Registering with intrinsic privileges because: A user should be able to mark as read their own notifications.
    superdesk.intrinsic_privilege(resource_name='activity', method=['PATCH'])


class ActivityResource(Resource):
    endpoint_name = 'activity'
    resource_methods = ['GET']
    item_methods = ['GET', 'PATCH']
    schema = {
        'name': {'type': 'string'},
        'message': {'type': 'string'},
        'data': {'type': 'dict'},
        'recipients': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'user_id': Resource.rel('users'),
                    'read': {'type': 'boolean', 'default': False},
                    'desk_id': Resource.rel('desks')
                }
            }
        },
        'item': Resource.rel('archive', type='string'),
        'item_slugline': {'type': 'string'},
        'user': Resource.rel('users'),
        'user_name': {'type': 'string'},
        'desk': Resource.rel('desks'),
        'resource': {'type': 'string'}
    }
    exclude = {endpoint_name, 'notification'}
    datasource = {
        'default_sort': [('_created', -1)],
        'filter': {'_created': {'$gte': utcnow() - datetime.timedelta(days=1)}}
    }
    superdesk.register_default_user_preference('email:notification', {
        'type': 'bool',
        'enabled': True,
        'default': True,
        'label': 'Send notifications via email',
        'category': 'notifications',
    })
    superdesk.register_default_user_preference('desktop:notification', {
        'type': 'bool',
        'enabled': True,
        'default': False,
        'label': 'Allow Desktop Notifications',
        'category': 'notifications',
    })


class ActivityService(BaseService):

    def get(self, req, lookup):
        """Filter out personal activity on personal items if inquired by another user."""
        if req is None:
            req = ParsedRequest()
        user = getattr(g, 'user', None)
        if not user:
            raise SuperdeskApiError.notFoundError('Can not determine user')
        where_cond = {}
        if req.where:
            if req.where[0] != '{':
                req.where = '{' + req.where + '}'
            where_cond = json.loads(req.where)
        for_user = where_cond.get('user', str(user.get('_id')))
        if for_user != str(user.get('_id')):
            where_item = {'$and': [{'desk': {'$ne': None}}, {'desk': {'$exists': True}},
                                   {'resource': 'archive'}]}
            where_cond['$or'] = [where_item, {'resource': {'$ne': 'archive'}}]
            req.where = json.dumps(where_cond)

        return self.backend.get(self.datasource, req=req, lookup=lookup)

    def on_update(self, updates, original):
        """Called on the patch request to mark a activity/notification/comment as read and nothing else

        :param updates:
        :param original:
        :return:
        """
        user = getattr(g, 'user', None)
        if not user:
            raise SuperdeskApiError.notFoundError('Can not determine user')
        user_id = user.get('_id')

        # make sure that the user making the read notification is in the notification list
        if not self.is_recipient(updates, user_id):
            raise SuperdeskApiError.forbiddenError('User is not in the notification list')

        # make sure the transition is from not read to read
        if not self.is_read(updates, user_id) and self.is_read(original, user_id):
            raise SuperdeskApiError.forbiddenError('Can not set notification as read')

        # make sure that no other users are being marked as read
        for recipient in updates.get('recipients', []):
            if recipient['user_id'] != user_id:
                if self.is_read(updates, recipient['user_id']) != self.is_read(original, recipient['user_id']):
                    raise SuperdeskApiError.forbiddenError('Can not set other users notification as read')

        # make sure that no other fields are being up dated just read and _updated
        if len(updates) != 2:
            raise SuperdeskApiError.forbiddenError('Can not update')

    def is_recipient(self, activity, user_id):
        """
        Checks if the given user is in the list of recipients
        """
        return any(r for r in activity.get('recipients', []) if r['user_id'] == user_id)

    def is_read(self, activity, user_id):
        """
        Returns the read value for the given user
        """
        return next((r['read'] for r in activity.get('recipients', []) if r['user_id'] == user_id), False)


ACTIVITY_CREATE = 'create'
ACTIVITY_UPDATE = 'update'
ACTIVITY_DELETE = 'delete'
ACTIVITY_EVENT = 'event'
ACTIVITY_ERROR = 'error'


def add_activity(activity_name, msg, resource=None, item=None, notify=None, notify_desks=None,
                 can_push_notification=True, **data):
    """
    Adds an activity into activity log.

    This will became part of current user activity log.
    If there is someone set to be notified it will make it into his notifications box.

    :param activity_name: Name of the activity
    :type activity_name: str
    :param msg: Message to be recorded in the activity log
    :type msg: str
    :param resource: resource name generating this activity
    :type resource: str
    :param item: article instance, if the activity is being recorded against an article, default None
    :type item: dict
    :param notify: user identifiers against whom the activity should be recorded, default None
    :type notify: list
    :param notify_desks: desk identifiers if someone mentions Desk Name in comments widget, default None
    :type notify_desks: list
    :param can_push_notification: flag indicating if a notification should be pushed via WebSocket, default True
    :type can_push_notification: bool
    :param data: kwargs
    :type data: dict
    :return: activity object
    :rtype: dict
    """

    activity = {
        'name': activity_name,
        'message': msg,
        'data': data,
        'resource': resource
    }

    user = getattr(g, 'user', None)
    if user:
        activity['user'] = user.get('_id')
        activity['user_name'] = user.get('display_name', user.get('username'))

    activity['recipients'] = []

    if notify:
        activity['recipients'] = [{'user_id': ObjectId(_id), 'read': False} for _id in notify]

    if notify_desks:
        activity['recipients'].extend([{'desk_id': ObjectId(_id), 'read': False} for _id in notify_desks])

    if item:
        if item.get('type') == 'text':
            activity['item'] = str(item.get('guid', item.get('_id')))
        else:
            # since guid and _id do not match for the item of type picture, audio and video
            # so sending _id as activity['item'] instead of guid for media items
            # and item_id for published media items as _id or guid does not match _id in archive for media items
            activity['item'] = str(item.get('item_id')) if item.get('state') in PUBLISH_STATES else str(item.get('_id'))

        activity['item_slugline'] = item.get('slugline', item.get('headline')) or item.get('unique_name')
        if item.get('task') and item['task'].get('desk'):
            activity['desk'] = ObjectId(item['task']['desk'])

    get_resource_service(ActivityResource.endpoint_name).post([activity])

    if can_push_notification:
        push_notification(ActivityResource.endpoint_name, _dest=activity['recipients'], activity=activity)

    return activity


def notify_and_add_activity(activity_name, msg, resource=None, item=None, user_list=None, **data):
    """
    Adds the activity and notify enabled and active users via email.
    """

    add_activity(activity_name, msg=msg, resource=resource, item=item,
                 notify=[str(user.get("_id")) for user in user_list] if user_list else None, **data)

    if activity_name == ACTIVITY_ERROR or user_list:
        recipients = get_recipients(user_list, activity_name)

        if activity_name != ACTIVITY_ERROR:
            current_user = getattr(g, 'user', None)
            activity = {
                'name': activity_name,
                'message': current_user.get('display_name') + ' ' + msg if current_user else msg,
                'data': data,
                'resource': resource
            }
        else:
            activity = {
                'name': activity_name,
                'message': 'System ' + msg,
                'data': data,
                'resource': resource
            }

        if recipients:
            send_activity_emails(activity=activity, recipients=recipients)


def get_recipients(user_list, activity_name):
    if not user_list and activity_name == ACTIVITY_ERROR:
        user_list = get_resource_service('users').get_users_by_user_type('administrator')

    recipients = [user.get('email') for user in user_list if not user.get('needs_activation', True) and
                  user.get('is_enabled', False) and user.get('is_active', False) and
                  get_resource_service('preferences')
                      .email_notification_is_enabled(preferences=user.get('user_preferences', {}))]

    return recipients


add_notifier(notify_and_add_activity)
