# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from apps.archive.archive import SOURCE as ARCHIVE
from apps.content import push_content_notification
from superdesk import get_resource_service
import superdesk
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.workflow import is_workflow_state_transition_valid


class TranslateResource(Resource):
    endpoint_name = 'translate'
    resource_title = endpoint_name

    schema = {
        'guid': {
            'type': 'string',
            'required': True
        },
        'language': {
            'type': 'string',
            'required': True
        }
    }

    url = 'archive/translate'

    resource_methods = ['POST']
    item_methods = []

    privileges = {'POST': 'translate'}


class TranslateService(BaseService):
    def create(self, docs, **kwargs):
        guid_of_translated_items = []

        for doc in docs:
            guid_of_item_to_be_translated = doc.get('guid')
            archive_service = get_resource_service(ARCHIVE)

            archived_doc = archive_service.find_one(req=None, _id=guid_of_item_to_be_translated)
            if not archived_doc:
                raise SuperdeskApiError.notFoundError('Fail to found item with guid: %s' %
                                                      guid_of_item_to_be_translated)

            if not is_workflow_state_transition_valid('translate', archived_doc[ITEM_STATE]):
                raise InvalidStateTransitionError()

            get_resource_service('macros').execute_translation_macro(
                archived_doc, archived_doc.get('language', None), doc.get('language'))
            archived_doc['language'] = doc.get('language')
            new_guid = archive_service.duplicate_content(archived_doc)
            guid_of_translated_items.append(new_guid)

            if kwargs.get('notify', True):
                push_content_notification([archived_doc])

        return guid_of_translated_items


superdesk.workflow_action(
    name='translate',
    exclude_states=[CONTENT_STATE.SPIKED, CONTENT_STATE.KILLED],
    privileges=['archive', 'translate']
)
