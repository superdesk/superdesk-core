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
import superdesk

from copy import copy

from eve.utils import ParsedRequest
from eve.versioning import resolve_document_version

from superdesk.users.services import current_user_has_privilege
from superdesk.resource import Resource
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.notification import push_notification
from superdesk.utc import utcnow
from superdesk.metadata.utils import item_url
from superdesk.services import BaseService
from superdesk.metadata.item import metadata_schema, ITEM_STATE, CONTENT_STATE, ITEM_TYPE
from superdesk import get_resource_service, config
from superdesk.activity import add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE
from superdesk.workflow import is_workflow_state_transition_valid
from apps.archive.common import get_item_expiry, item_operations, ITEM_OPERATION, update_version, \
    insert_into_versions, is_assigned_to_a_desk, convert_task_attributes_to_objectId, on_create_item, \
    ARCHIVE, get_subject
from flask_babel import _

task_statuses = ['todo', 'in_progress', 'done']
default_status = 'todo'
ITEM_SEND = 'send'
item_operations.append(ITEM_SEND)
MACRO_INCOMING = 'incoming'
MACRO_OUTGOING = 'outgoing'
MACRO_ONSTAGE = 'onstage'

logger = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = 'tasks'
    service = TasksService(TaskResource.datasource['source'], backend=superdesk.get_backend())
    TaskResource(endpoint_name, app=app, service=service)


def compare_dictionaries(original, updates):
    original_keys = set(original.keys())
    updates_keys = set(updates.keys())
    intersect_keys = original_keys.intersection(updates_keys)
    added = list(updates_keys - original_keys)
    modified = [o for o in intersect_keys if original[o] != updates[o]]
    modified.extend(added)
    return modified


def send_to(doc, update=None, desk_id=None, stage_id=None, user_id=None, default_stage='incoming_stage'):
    """Send item to given desk and stage.

    Applies the outgoing and incoming macros of current and destination stages

    :param doc: original document to be sent
    :param update: updates for the document
    :param desk: id of desk where item should be sent
    :param stage: optional stage within the desk
    :param default_stage: if no stage_id is passed then it determines the stage in that desk the doc is assigned,
            either the the incomming stage or the working stage.
    """

    original_task = doc.setdefault('task', {})
    current_stage = None
    if original_task.get('stage'):
        current_stage = get_resource_service('stages').find_one(req=None, _id=original_task.get('stage'))
    desk = destination_stage = None
    task = {'desk': desk_id, 'stage': stage_id, 'user': original_task.get('user') if user_id is None else user_id}

    if current_stage:
        apply_stage_rule(doc, update, current_stage, MACRO_OUTGOING)

    if desk_id:
        desk = superdesk.get_resource_service('desks').find_one(req=None, _id=desk_id)
        if not desk:
            raise SuperdeskApiError.notFoundError(_('Invalid desk identifier {desk_id}').format(desk_id=desk_id))

        if not current_user_has_privilege('move') and \
                str(user_id) not in [str(x.get('user', '')) for x in desk.get('members', [])]:
            raise SuperdeskApiError.forbiddenError(_('User is not member of desk: {desk_id}').format(desk_id=desk_id))

        task['desk'] = desk_id
        if not stage_id:
            task['stage'] = desk.get(default_stage)
            destination_stage = get_resource_service('stages').find_one(req=None, _id=desk.get(default_stage))

    if stage_id:
        destination_stage = get_resource_service('stages').find_one(req=None, _id=stage_id)
        if not destination_stage:
            raise SuperdeskApiError.notFoundError(_('Invalid stage identifier {stage_id}').format(stage_id=stage_id))

        task['desk'] = destination_stage['desk']
        task['stage'] = stage_id

    if destination_stage:
        apply_stage_rule(doc, update, destination_stage, MACRO_INCOMING, desk=desk, task=task)
        if destination_stage.get('task_status'):
            task['status'] = destination_stage['task_status']

    if update:
        update.setdefault('task', {})
        update['task'].update(task)
        update['expiry'] = get_item_expiry(desk=desk, stage=destination_stage)
    else:
        doc['task'].update(task)
        doc['expiry'] = get_item_expiry(desk=desk, stage=destination_stage)
        superdesk.get_resource_service('desks').apply_desk_metadata(doc, doc)


def apply_stage_rule(doc, update, stage, rule_type, desk=None, task=None):
    macro_type = '{}_macro'.format(rule_type)

    if stage.get(macro_type):
        try:
            original_doc = dict(doc)
            macro = get_resource_service('macros').get_macro_by_name(stage.get(macro_type))
            if not macro:
                logger.warning('macro %s is missing', stage.get(macro_type))
                return
            macro['callback'](doc, desk=desk, stage=stage, task=task)
            if update:
                modified = compare_dictionaries(original_doc, doc)
                for i in modified:
                    update[i] = doc[i]
        except Exception as ex:
            message = _('Error:{exception} in {rule_type} rule:{rule} for stage:{stage}').format(
                exception=str(ex), rule_type=rule_type, rule=macro.get('label'), stage=stage.get('name'))
            raise SuperdeskApiError.badRequestError(message)


def apply_onstage_rule(doc, _id):
    """Apply any on stage macro/rule that may be defined for the stage.

    :param doc:
    :param _id:
    :return:
    """
    doc[config.ID_FIELD] = _id
    stage = get_resource_service('stages').find_one(req=None, _id=doc.get('task', {}).get('stage'))
    if stage:
        apply_stage_rule(doc, None, stage, 'onstage')


class TaskResource(Resource):
    datasource = {
        'source': 'archive',
        'default_sort': [('_updated', -1)],
        'filter': {'task': {'$exists': True}},
        'elastic_filter': {'bool': {
            'must': {'exists': {'field': 'task'}},
            'must_not': {'term': {ITEM_STATE: 'spiked'}},
        }}
    }

    item_url = item_url
    schema = {
        'expiry': {'type': 'string'},
        'slugline': metadata_schema['slugline'],
        'description_text': metadata_schema['description_text'],
        'type': metadata_schema['type'],
        'task': {
            'type': 'dict',
            'schema': {
                'status': {
                    'type': 'string',
                    'allowed': task_statuses,
                    'default': default_status
                },
                'due_date': {'type': 'datetime'},
                'started_at': {'type': 'datetime'},
                'finished_at': {'type': 'datetime'},
                'user': Resource.rel('users', True),
                'desk': Resource.rel('desks', True),
                'stage': Resource.rel('stages', True)
            }
        }
    }
    privileges = {'POST': 'tasks', 'PATCH': 'tasks', 'DELETE': 'tasks'}


class TasksService(BaseService):

    def get(self, req, lookup):
        if req is None:
            req = ParsedRequest()
        return self.backend.get('tasks', req=req, lookup=lookup)

    def update_times(self, doc):
        task = doc.get('task', {})
        status = task.get('status', None)
        if status == 'in_progress':
            task.setdefault('started_at', utcnow())

        if status == 'done':
            task.setdefault('finished_at', utcnow())

    def __is_content_moved_from_desk(self, doc):
        """
        Returns True if the 'doc' is being moved from a desk. False otherwise.
        """
        return doc.get('task', {}).get('desk', None) is None

    def __is_content_assigned_to_new_desk(self, original, updates):
        """Checks if the content is assigned to a new desk.

        :return: True if the content is being moved to a new desk. False otherwise.
        """
        return str(original.get('task', {}).get('desk', '')) != str(updates.get('task', {}).get('desk', ''))

    def __update_state(self, updates, original):
        if self.__is_content_assigned_to_new_desk(original, updates):
            # check if the preconditions for the action are in place
            original_state = original[ITEM_STATE]
            if not is_workflow_state_transition_valid('move', original_state):
                raise InvalidStateTransitionError()

            updates[ITEM_STATE] = CONTENT_STATE.DRAFT if self.__is_content_moved_from_desk(updates) \
                else CONTENT_STATE.SUBMITTED
            resolve_document_version(updates, ARCHIVE, 'PATCH', original)

    def update_stage(self, doc):
        task = doc.get('task', {})
        desk_id = task.get('desk', None)
        stage_id = task.get('stage', None)
        send_to(doc=doc, desk_id=desk_id, stage_id=stage_id)

    def on_create(self, docs):
        on_create_item(docs)
        for doc in docs:
            resolve_document_version(doc, ARCHIVE, 'POST')
            self.update_times(doc)
            self.update_stage(doc)
            convert_task_attributes_to_objectId(doc)

    def on_created(self, docs):
        push_notification(self.datasource, created=1)
        push_notification('task:new')
        for doc in docs:
            insert_into_versions(doc['_id'])
            if is_assigned_to_a_desk(doc):
                add_activity(ACTIVITY_CREATE, 'added new task {{ subject }} of type {{ type }}',
                             self.datasource, item=doc,
                             subject=get_subject(doc), type=doc[ITEM_TYPE])

    def on_update(self, updates, original):
        self.update_times(updates)
        if is_assigned_to_a_desk(updates):
            self.__update_state(updates, original)
        new_stage_id = str(updates.get('task', {}).get('stage', ''))
        old_stage_id = str(original.get('task', {}).get('stage', ''))
        new_user_id = updates.get('task', {}).get('user', '')
        if new_stage_id and new_stage_id != old_stage_id:
            updates[ITEM_OPERATION] = ITEM_SEND
            send_to(doc=original, update=updates, desk_id=None, stage_id=new_stage_id, user_id=new_user_id)
            resolve_document_version(updates, ARCHIVE, 'PATCH', original)
        convert_task_attributes_to_objectId(updates)
        update_version(updates, original)

    def on_updated(self, updates, original):
        updated = copy(original)
        updated.update(updates)
        if self._stage_changed(updates, original):
            insert_into_versions(doc=updated)
        new_task = updates.get('task', {})
        old_task = original.get('task', {})
        if new_task.get('stage') != old_task.get('stage'):
            push_notification('task:stage',
                              new_stage=str(new_task.get('stage', '')),
                              old_stage=str(old_task.get('stage', '')),
                              new_desk=str(new_task.get('desk', '')),
                              old_desk=str(old_task.get('desk', ''))
                              )
        else:
            push_notification(self.datasource, updated=1)

        if is_assigned_to_a_desk(updated):
            if self.__is_content_assigned_to_new_desk(original, updates) and \
                    not self._stage_changed(updates, original):
                insert_into_versions(doc=updated)
            add_activity(ACTIVITY_UPDATE, 'updated task {{ subject }} for item {{ type }}',
                         self.datasource, item=updated, subject=get_subject(updated), type=updated['type'])

    def on_deleted(self, doc):
        push_notification(self.datasource, deleted=1)

    def assign_user(self, item_id, user):
        return self.patch(item_id, {'task': user})

    def _stage_changed(self, updates, original):
        new_stage_id = str(updates.get('task', {}).get('stage', ''))
        old_stage_id = str(original.get('task', {}).get('stage', ''))
        return new_stage_id and new_stage_id != old_stage_id


superdesk.privilege(name='tasks', label='Tasks Management', description='Tasks Management')
