# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json

from eve.utils import config, ParsedRequest
from flask import request

import superdesk
from apps.archive.archive import SOURCE as ARCHIVE
from apps.auth import get_user
from apps.content import push_content_notification
from apps.tasks import send_to
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE
from superdesk.metadata.utils import item_url
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.utc import utcnow


class DuplicateResource(Resource):
    endpoint_name = 'duplicate'
    resource_title = endpoint_name

    schema = {
        'desk': Resource.rel('desks', False, required=True),
        'stage': Resource.rel('stages', False, required=False),
        'type': {
            'type': 'string',
            'required': True
        },
        'item_id': {
            'type': 'string',
            'required': False
        }
    }

    url = 'archive/<{0}:guid>/duplicate'.format(item_url)

    resource_methods = ['POST']
    item_methods = []

    privileges = {'POST': 'duplicate'}


class DuplicateService(BaseService):
    def create(self, docs, **kwargs):
        guid_of_item_to_be_duplicated = request.view_args['guid']

        guid_of_duplicated_items = []

        for doc in docs:
            archive_service = get_resource_service(ARCHIVE)
            archived_doc = {}

            if doc.get('type') == 'archived':
                archived_service = get_resource_service('archived')
                req = ParsedRequest()
                query = {'query':
                         {'filtered':
                          {'filter':
                           {'bool':
                            {'must': [
                                {'term': {'item_id': doc.get('item_id')}}
                            ]}}}}, "sort": [{"_current_version": "desc"}], "size": 1}
                req.args = {'source': json.dumps(query)}
                archived_docs = archived_service.get(req=req, lookup=None)
                if archived_docs.count() > 0:
                    archived_doc = archived_docs[0]

            else:
                archived_doc = archive_service.find_one(req=None, _id=guid_of_item_to_be_duplicated)

            self._validate(archived_doc, doc, guid_of_item_to_be_duplicated)

            # reset timestamps
            archived_doc['versioncreated'] = archived_doc['firstcreated'] = utcnow()
            archived_doc['firstpublished'] = None

            send_to(doc=archived_doc, desk_id=doc.get('desk'), stage_id=doc.get('stage'), default_stage='working_stage')
            new_guid = archive_service.duplicate_content(archived_doc)
            guid_of_duplicated_items.append(new_guid)

        if kwargs.get('notify', True):
            push_content_notification([archived_doc])

        return guid_of_duplicated_items

    def _validate(self, doc_in_archive, doc, guid_to_duplicate):
        """Validates if the given archived_doc is still eligible to be duplicated.

        Rules:
            1. Is the item requested found in archive collection?
            2. Is workflow transition valid?
            3. Is item locked by another user?

        :param doc_in_archive: object representing the doc in archive collection
        :type doc_in_archive: dict
        :param doc: object received as part of request
        :type doc: dict
        :param guid_to_duplicate: GUID of the item to duplicate
        :type guid_to_duplicate: str
        :raises
            SuperdeskApiError.notFoundError: If doc_in_archive is None
            SuperdeskApiError.forbiddenError: if item is locked
            InvalidStateTransitionError: if workflow transition is invalid
        """

        if not doc_in_archive:
            raise SuperdeskApiError.notFoundError('Fail to found item with guid: %s' % guid_to_duplicate)

        if not is_workflow_state_transition_valid('duplicate', doc_in_archive[ITEM_STATE]):
            raise InvalidStateTransitionError()

        lock_user = doc_in_archive.get('lock_user', None)
        force_unlock = doc_in_archive.get('force_unlock', False)
        user = get_user()
        str_user_id = str(user.get(config.ID_FIELD)) if user else None
        if lock_user and str(lock_user) != str_user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError('The item was locked by another user')


superdesk.workflow_action(
    name='duplicate',
    exclude_states=[CONTENT_STATE.SPIKED, CONTENT_STATE.KILLED],
    privileges=['archive', 'duplicate']
)
