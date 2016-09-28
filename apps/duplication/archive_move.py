# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from eve.utils import config
from eve.versioning import resolve_document_version
from flask import request
from copy import deepcopy

import superdesk
from apps.tasks import send_to, apply_onstage_rule
from apps.packages.takes_package_service import TakesPackageService
from apps.desks import DeskTypes
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, SIGN_OFF
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.metadata.utils import item_url
from apps.archive.common import insert_into_versions, item_operations,\
    ITEM_OPERATION, set_sign_off, get_user, LAST_AUTHORING_DESK, LAST_PRODUCTION_DESK,\
    convert_task_attributes_to_objectId
from apps.archive.archive import SOURCE as ARCHIVE
from superdesk.workflow import is_workflow_state_transition_valid
from apps.content import push_item_move_notification
from superdesk.lock import lock, unlock

ITEM_MOVE = 'move'
item_operations.append(ITEM_MOVE)


class MoveResource(Resource):
    endpoint_name = 'move'
    resource_title = endpoint_name

    schema = {
        'task': {
            'type': 'dict',
            'required': True,
            'schema': {
                'desk': Resource.rel('desks', False, required=True),
                'stage': Resource.rel('stages', False, required=True)
            }
        }
    }

    url = 'archive/<{0}:guid>/move'.format(item_url)

    resource_methods = ['POST']
    item_methods = []

    privileges = {'POST': 'move'}


class MoveService(BaseService):
    def create(self, docs, **kwargs):
        guid_of_item_to_be_moved = request.view_args['guid']
        guid_of_moved_items = []

        # set the lock_id it per item
        lock_id = "item_move {}".format(guid_of_item_to_be_moved)

        if not lock(lock_id, expire=5):
            raise SuperdeskApiError.forbiddenError(message="Item is locked for move by another user.")

        try:
            # doc represents the target desk and stage
            doc = docs[0]
            moved_item = self.move_content(guid_of_item_to_be_moved, doc)
            guid_of_moved_items.append(moved_item.get(config.ID_FIELD))
            return guid_of_moved_items
        except Exception as e:
            raise e
        finally:
            unlock(lock_id)

    def move_content(self, id, doc):
        archive_service = get_resource_service(ARCHIVE)
        archived_doc = archive_service.find_one(req=None, _id=id)

        if not archived_doc:
            raise SuperdeskApiError.notFoundError('Fail to found item with guid: %s' % id)

        self._validate(archived_doc, doc)
        self._move(archived_doc, doc)

        # move the takes package where the first take is located.
        takes_service = TakesPackageService()
        takes_package = takes_service.get_take_package(archived_doc)
        if takes_package and \
                takes_service.get_take_by_take_no(archived_doc, package=takes_package) == id:
            self._move(takes_package, doc)

        # get the recent updates again
        archived_doc = archive_service.find_one(req=None, _id=id)
        # finally apply any on stage rules/macros
        apply_onstage_rule(archived_doc, id)

        return archived_doc

    def _move(self, archived_doc, doc):
        archive_service = get_resource_service(ARCHIVE)
        original = deepcopy(archived_doc)
        user = get_user()
        send_to(doc=archived_doc, desk_id=doc.get('task', {}).get('desk'), stage_id=doc.get('task', {}).get('stage'),
                user_id=user.get(config.ID_FIELD))
        if archived_doc[ITEM_STATE] not in {CONTENT_STATE.PUBLISHED, CONTENT_STATE.SCHEDULED, CONTENT_STATE.KILLED}:
            archived_doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED
        archived_doc[ITEM_OPERATION] = ITEM_MOVE
        # set the change in desk type when content is moved.
        self.set_change_in_desk_type(archived_doc, original)
        archived_doc.pop(SIGN_OFF, None)
        set_sign_off(archived_doc, original=original)
        convert_task_attributes_to_objectId(archived_doc)
        resolve_document_version(archived_doc, ARCHIVE, 'PATCH', original)
        del archived_doc[config.ID_FIELD]
        archive_service.update(original[config.ID_FIELD], archived_doc, original)
        insert_into_versions(id_=original[config.ID_FIELD])
        push_item_move_notification(original, archived_doc)

    def _validate(self, archived_doc, doc):
        """Validate that the item can be move.

        :param dict archived_doc: item to be moved
        :param dict doc: new location details
        """
        current_stage_of_item = archived_doc.get('task', {}).get('stage')
        if current_stage_of_item and str(current_stage_of_item) == str(doc.get('task', {}).get('stage')):
            raise SuperdeskApiError.preconditionFailedError(message='Move is not allowed within the same stage.')
        if not is_workflow_state_transition_valid('submit_to_desk', archived_doc[ITEM_STATE]):
            raise InvalidStateTransitionError()

    def set_change_in_desk_type(self, updated, original):
        """Detects if the change in the desk is between authoring to production (and vice versa).

        Sets the field 'last_production_desk' and 'last_authoring_desk'.

        :param dict updated: document to be saved
        :param dict original: original document
        """
        old_desk_id = str(original.get('task', {}).get('desk', ''))
        new_desk_id = str(updated.get('task', {}).get('desk', ''))
        if old_desk_id and old_desk_id != new_desk_id:
            old_desk = get_resource_service('desks').find_one(req=None, _id=old_desk_id)
            new_desk = get_resource_service('desks').find_one(req=None, _id=new_desk_id)
            if old_desk.get('desk_type', '') != new_desk.get('desk_type', ''):
                if new_desk.get('desk_type') == DeskTypes.production.value:
                    updated['task'][LAST_AUTHORING_DESK] = old_desk_id
                else:
                    updated['task'][LAST_PRODUCTION_DESK] = old_desk_id


superdesk.workflow_action(
    name='submit_to_desk',
    include_states=['draft', 'fetched', 'routed', 'submitted', 'in_progress', 'published', 'scheduled'],
    privileges=['archive', 'move']
)
