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
from apps.auth import get_user, get_user_id
from eve.versioning import resolve_document_version
from flask import request, current_app as app
from superdesk import get_resource_service, Service, config
from superdesk.metadata.item import (ITEM_STATE, EMBARGO, CONTENT_STATE, CONTENT_TYPE,
                                     ASSOCIATIONS, PROCESSED_FROM, metadata_schema)
from superdesk.resource import Resource, build_custom_hateoas
from apps.archive.common import (CUSTOM_HATEOAS, ARCHIVE, ITEM_UNLINK,
                                 insert_into_versions, ITEM_CORRECTION)
from superdesk.metadata.utils import item_url
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.notification import push_notification
from apps.tasks import send_to
from apps.archive.archive import update_associations
from flask_babel import _

logger = logging.getLogger(__name__)


class ArchiveCorrectionResource(Resource):
    endpoint_name = 'archive_correction'
    resource_title = endpoint_name

    schema = metadata_schema.copy()
    schema.update({
        'desk_id': {'type': 'string', 'nullable': True},
        'update': {'type': 'dict', 'nullable': True, 'allow_unknown': True},
        '_links': {'type': 'dict'},
    })

    datasource = {
        'source': 'archive',
        'search_backend': 'elastic',
    }

    url = 'archive/<{0}:original_id>/correction'.format(item_url)
    resource_methods = ['POST', 'DELETE']
    privileges = {'POST': 'correct', 'DELETE': 'correct'}


class ArchiveCorrectionService(Service):
    def get(self, req, lookup):
        if lookup.get('original_id'):
            return super().get(req, {'_id': lookup['original_id']})
        return super().get(req, lookup)

    def create(self, docs, **kwargs):
        doc = docs[0] if len(docs) > 0 else {}
        original_id = request.view_args['original_id']

        archive_service = get_resource_service(ARCHIVE)
        original = archive_service.find_one(req=None, _id=original_id)
        self._validate_correction(original)

        correction = self._create_correction_article(original,
                                                     desk_id=doc.get('desk_id'))

        # Set the version.
        resolve_document_version(correction, ARCHIVE, "POST")
        ids = archive_service.post([correction])
        insert_into_versions(doc=correction)
        build_custom_hateoas(CUSTOM_HATEOAS, correction)

        self._add_being_correction_flag(original, correction)

        doc.clear()
        doc.update(correction)
        return ids

    def _validate_correction(self, original):
        """Validates the article to be corrected.

        :param original: article to be corrected.
        :raises: SuperdeskApiError
        """
        if not original:
            raise SuperdeskApiError.notFoundError(message=_('Cannot find the article'))

        if (not is_workflow_state_transition_valid('correction', original[ITEM_STATE])
                and not config.ALLOW_UPDATING_SCHEDULED_ITEMS):
            raise InvalidStateTransitionError()

    def _create_correction_article(self, original, desk_id):
        """Creates a new story and sets the metadata from original and update.

        :param dict original: original story
        :param dict updates: updates story
        :return:new story with updated values
        """
        correction = dict()

        fields = ['family_id', 'event_id', 'flags', 'language', ASSOCIATIONS, 'extra', 'fields_meta']

        # ingest provider and source to be retained for new item
        fields.extend(['ingest_provider', 'source'])
        if original.get('profile'):
            content_type = get_resource_service('content_types').find_one(req=None, _id=original['profile'])
            extended_fields = list(content_type['schema'].keys())
            # extra fields needed.
            extended_fields.extend(['profile', 'keywords', 'target_regions',
                                    'target_types', 'target_subscribers'])
        else:
            extended_fields = [
                'abstract', 'anpa_category', 'pubstatus', 'slugline', 'urgency',
                'subject', 'priority', 'byline', 'dateline', 'headline', 'place',
                'genre', 'body_footer', 'company_codes', 'keywords',
                'target_regions', 'target_types', 'target_subscribers', 'type'
            ]

        fields.extend(extended_fields)
        # if the field is present in original, add it
        for field in fields:
            if original.get(field):
                correction[field] = original.get(field, original.get(field))

        if 'body_html' in correction:
            if 'fields_meta' in original:
                correction['fields_meta'] = original.get('fields_meta')
            update_associations(correction)

        # if the original was flagged for SMS the correction should not be.
        if correction.get('flags', {}).get('marked_for_sms', False):
            correction['flags']['marked_for_sms'] = False

        correction['corrected_of'] = original[config.ID_FIELD]
        correction['correction_sequence'] = (original.get('correction_sequence') or 0) + 1
        correction.pop(PROCESSED_FROM, None)

        # send the document to the desk only if a new correction is created
        send_to(doc=correction, desk_id=(original['task']['desk']),
                default_stage='working_stage', user_id=get_user_id())

        correction[ITEM_STATE] = CONTENT_STATE.CORRECTION
        correction['type'] = original.get('type')
        return correction

    def _add_being_correction_flag(self, original, correction):
        """Adds correction_by field to the existing published items."""

        get_resource_service('published').update_published_items(original[config.ID_FIELD],
                                                                 'correction_by', correction[config.ID_FIELD])
        get_resource_service('published').update_published_items(original[config.ID_FIELD],
                                                                 ITEM_STATE, CONTENT_STATE.BEING_CORRECTED)

        # modify the original item as well.
        get_resource_service(ARCHIVE).system_update(original[config.ID_FIELD],
                                                    {'correction_by': correction[config.ID_FIELD],
                                                     ITEM_STATE: CONTENT_STATE.BEING_CORRECTED},
                                                    original)
        app.on_archive_item_updated({'correction_by': correction[config.ID_FIELD],
                                     ITEM_STATE: CONTENT_STATE.BEING_CORRECTED},
                                    original, ITEM_CORRECTION)

    def delete(self, lookup):
        target_id = request.view_args['original_id']
        archive_service = get_resource_service(ARCHIVE)
        published_service = get_resource_service('published')

        target = archive_service.find_one(req=None, _id=target_id)

        # for modifing the original item.
        archive_items = archive_service.find({'_id': target['corrected_of']})

        being_corrected_articles = published_service.find({
            'guid': target.get('corrected_of'),
            ITEM_STATE: CONTENT_STATE.BEING_CORRECTED
        })

        for item in being_corrected_articles:
            published_service.patch(id=item['_id'], updates={'state': CONTENT_STATE.PUBLISHED})

        # modify the original item as well.
        for archive_item in archive_items:
            get_resource_service(ARCHIVE).system_update(archive_item['_id'],
                                                        {ITEM_STATE: CONTENT_STATE.PUBLISHED},
                                                        archive_item)
            app.on_archive_item_updated({ITEM_STATE: CONTENT_STATE.PUBLISHED},
                                        archive_item, ITEM_UNLINK)

        archive_service.delete({'_id': target_id})

        user = get_user(required=True)
        push_notification('item:unlink', item=target_id, user=str(user.get(config.ID_FIELD)))
