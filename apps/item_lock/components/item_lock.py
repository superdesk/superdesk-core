# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
import logging
import superdesk

from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE, PUBLISH_STATES
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from superdesk.users.services import current_user_has_privilege
from superdesk.utc import utcnow
from superdesk.lock import lock, unlock
from eve.utils import config
from eve.versioning import resolve_document_version, insert_versioning_documents

from apps.common.components.base_component import BaseComponent
from apps.common.models.utils import get_model
from apps.content import push_content_notification
from apps.packages.package_service import PackageService
from ..models.item import ItemModel


LOCK_USER = 'lock_user'
LOCK_SESSION = 'lock_session'
STATUS = '_status'
TASK = 'task'
logger = logging.getLogger(__name__)


def push_unlock_notification(item, user_id, session_id):
    push_notification(
        'item:unlock',
        item=str(item.get(config.ID_FIELD)),
        item_version=str(item.get(config.VERSION)),
        state=item.get(ITEM_STATE),
        user=str(user_id),
        lock_session=str(session_id),
        _etag=item.get(config.ETAG)
    )


class ItemLock(BaseComponent):
    def __init__(self, app):
        self.app = app
        self.app.on_session_end += self.on_session_end

    @classmethod
    def name(cls):
        return 'item_lock'

    def lock(self, item_filter, user_id, session_id, action):
        item_model = get_model(ItemModel)
        item = item_model.find_one(item_filter)

        # set the lock_id it per item
        lock_id = "item_lock {}".format(item.get(config.ID_FIELD))

        if not item:
            raise SuperdeskApiError.notFoundError()

        # get the lock it not raise forbidden exception
        if not lock(lock_id, expire=5):
            raise SuperdeskApiError.forbiddenError(message="Item is locked by another user.")

        try:
            can_user_lock, error_message = self.can_lock(item, user_id, session_id)

            if can_user_lock:
                self.app.on_item_lock(item, user_id)
                updates = {LOCK_USER: user_id, LOCK_SESSION: session_id, 'lock_time': utcnow()}
                if action:
                    updates['lock_action'] = action

                item_model.update(item_filter, updates)

                if item.get(TASK):
                    item[TASK]['user'] = user_id
                else:
                    item[TASK] = {'user': user_id}

                superdesk.get_resource_service('tasks').assign_user(item[config.ID_FIELD], item[TASK])
                self.app.on_item_locked(item, user_id)
                item = item_model.find_one(item_filter)
                push_notification('item:lock',
                                  item=str(item.get(config.ID_FIELD)),
                                  item_version=str(item.get(config.VERSION)),
                                  user=str(user_id), lock_time=updates['lock_time'],
                                  lock_session=str(session_id),
                                  _etag=item.get(config.ETAG))
            else:
                raise SuperdeskApiError.forbiddenError(message=error_message)

            item = item_model.find_one(item_filter)
            return item
        finally:
            # unlock the lock :)
            unlock(lock_id, remove=True)

    def unlock(self, item_filter, user_id, session_id, etag):
        item_model = get_model(ItemModel)
        item = item_model.find_one(item_filter)

        if not item:
            raise SuperdeskApiError.notFoundError()

        if not item.get(LOCK_USER):
            raise SuperdeskApiError.badRequestError(message="Item is not locked.")

        can_user_unlock, error_message = self.can_unlock(item, user_id)

        if can_user_unlock:
            self.app.on_item_unlock(item, user_id)
            updates = {}

            # delete the item if nothing is saved so far
            # version 0 created on lock item
            if item.get(config.VERSION, 0) == 0 and item[ITEM_STATE] == CONTENT_STATE.DRAFT:
                if item.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
                    # if item is composite then update referenced items in package.
                    PackageService().update_groups({}, item)

                superdesk.get_resource_service('archive').delete_action(lookup={'_id': item['_id']})
                push_content_notification([item])
            else:
                updates = {LOCK_USER: None, LOCK_SESSION: None, 'lock_time': None,
                           'lock_action': None, 'force_unlock': True}
                autosave = superdesk.get_resource_service('archive_autosave').find_one(req=None, _id=item['_id'])
                if autosave and item[ITEM_STATE] not in PUBLISH_STATES:
                    if not hasattr(flask.g, 'user'):  # user is not set when session expires
                        flask.g.user = superdesk.get_resource_service('users').find_one(req=None, _id=user_id)
                    autosave.update(updates)
                    resolve_document_version(autosave, 'archive', 'PATCH', item)
                    superdesk.get_resource_service('archive').patch(item['_id'], autosave)
                    item = superdesk.get_resource_service('archive').find_one(req=None, _id=item['_id'])
                    insert_versioning_documents('archive', item)
                else:
                    item_model.update(item_filter, updates)
                    item = item_model.find_one(item_filter)
                self.app.on_item_unlocked(item, user_id)

            push_unlock_notification(item, user_id, session_id)
        else:
            raise SuperdeskApiError.forbiddenError(message=error_message)

        return item

    def unlock_session(self, user_id, session_id):
        item_model = get_model(ItemModel)
        items = item_model.find({'lock_session': session_id})

        for item in items:
            self.unlock({'_id': item['_id']}, user_id, session_id, None)

    def can_lock(self, item, user_id, session_id):
        """
        Function checks whether user can lock the item or not. If not then raises exception.
        """
        can_user_edit, error_message = superdesk.get_resource_service('archive').can_edit(item, user_id)

        if can_user_edit:
            if item.get(LOCK_USER):
                if str(item.get(LOCK_USER, '')) == str(user_id) and str(item.get(LOCK_SESSION)) != str(session_id):
                    return False, 'Item is locked by you in another session.'
                else:
                    if str(item.get(LOCK_USER, '')) != str(user_id):
                        return False, 'Item is locked by another user.'
        else:
            return False, error_message

        return True, ''

    def can_unlock(self, item, user_id):
        """
        Function checks whether user can unlock the item or not.
        """
        can_user_edit, error_message = superdesk.get_resource_service('archive').can_edit(item, user_id)

        if can_user_edit:
            if not (str(item.get(LOCK_USER, '')) == str(user_id) or
                    (current_user_has_privilege('archive') and current_user_has_privilege('unlock'))):
                return False, 'You don\'t have permissions to unlock an item.'
        else:
            return False, error_message

        return True, ''

    def on_session_end(self, user_id, session_id):
        self.unlock_session(user_id, session_id)
