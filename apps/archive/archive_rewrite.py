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
from apps.auth import get_user
from eve.versioning import resolve_document_version
from flask import request, current_app as app
from apps.archive import ArchiveSpikeService
from superdesk import get_resource_service, Service, config
from superdesk.metadata.item import ITEM_STATE, EMBARGO, CONTENT_STATE, CONTENT_TYPE, \
    ITEM_TYPE, PUBLISH_STATES, ASSOCIATIONS, GUID_TAG
from superdesk.resource import Resource, build_custom_hateoas
from apps.archive.common import CUSTOM_HATEOAS, ITEM_CREATE, ARCHIVE, BROADCAST_GENRE, ITEM_REWRITE, \
    ITEM_UNLINK, ITEM_LINK, insert_into_versions
from superdesk.metadata.utils import item_url, generate_guid
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.notification import push_notification
from apps.tasks import send_to
from apps.archive.archive import update_associations

logger = logging.getLogger(__name__)


class ArchiveRewriteResource(Resource):
    endpoint_name = 'archive_rewrite'
    resource_title = endpoint_name

    schema = {
        'desk_id': {'type': 'string', 'nullable': True},
        'update': {'type': 'dict', 'nullable': True}
    }

    url = 'archive/<{0}:original_id>/rewrite'.format(item_url)
    resource_methods = ['POST', 'DELETE']
    privileges = {'POST': 'rewrite', 'DELETE': 'rewrite'}


class ArchiveRewriteService(Service):
    def create(self, docs, **kwargs):
        doc = docs[0] if len(docs) > 0 else {}
        original_id = request.view_args['original_id']
        update_document = doc.get('update')

        archive_service = get_resource_service(ARCHIVE)
        original = archive_service.find_one(req=None, _id=original_id)
        self._validate_rewrite(original, update_document)

        rewrite = self._create_rewrite_article(original,
                                               existing_item=update_document,
                                               desk_id=doc.get('desk_id'))

        if 'body_html' in rewrite:
            if 'editor_state' in original:
                rewrite['editor_state'] = original['editor_state']
            update_associations(rewrite)

        if update_document:
            # process the existing story
            archive_service.patch(update_document[config.ID_FIELD], rewrite)
            app.on_archive_item_updated(rewrite, update_document, ITEM_LINK)
            rewrite[config.ID_FIELD] = update_document[config.ID_FIELD]
            ids = [update_document[config.ID_FIELD]]
        else:
            # Set the version.
            resolve_document_version(rewrite, ARCHIVE, "POST")
            ids = archive_service.post([rewrite])
            insert_into_versions(doc=rewrite)
            build_custom_hateoas(CUSTOM_HATEOAS, rewrite)

            app.on_archive_item_updated({'rewrite_of': rewrite.get('rewrite_of')}, rewrite, ITEM_LINK)

        self._add_rewritten_flag(original, rewrite)
        get_resource_service('archive_broadcast').on_broadcast_master_updated(ITEM_CREATE,
                                                                              item=original,
                                                                              rewrite_id=ids[0])

        doc.clear()
        doc.update(rewrite)
        return ids

    def _validate_rewrite(self, original, update):
        """Validates the article to be rewritten.

        :param original: article to be rewritten
        :param update: article as the rewrite
        :raises: SuperdeskApiError
        """
        if not original:
            raise SuperdeskApiError.notFoundError(message='Cannot find the article')

        if original.get(EMBARGO):
            raise SuperdeskApiError.badRequestError("Rewrite of an Item having embargo isn't possible")

        if not original.get('event_id'):
            raise SuperdeskApiError.notFoundError(message='Event id does not exist')

        if original.get('rewritten_by'):
            raise SuperdeskApiError.badRequestError(message='Article has been rewritten before !')

        if not is_workflow_state_transition_valid('rewrite', original[ITEM_STATE]):
            raise InvalidStateTransitionError()

        if original.get('rewrite_of') and not (original.get(ITEM_STATE) in PUBLISH_STATES):
            raise SuperdeskApiError.badRequestError(message="Rewrite is not published. Cannot rewrite the story again.")

        if update:
            # in case of associate as update
            if update.get('rewrite_of'):
                raise SuperdeskApiError.badRequestError("Rewrite story has been used as update before !")

            if update.get(ITEM_STATE) in [CONTENT_STATE.PUBLISHED,
                                          CONTENT_STATE.CORRECTED,
                                          CONTENT_STATE.KILLED,
                                          CONTENT_STATE.SCHEDULED,
                                          CONTENT_STATE.SPIKED]:
                raise InvalidStateTransitionError()

            if update.get(ITEM_TYPE) not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
                raise SuperdeskApiError.badRequestError("Rewrite story can only be text or pre-formatted !")

            if update.get('genre') and \
                    any(genre.get('value', '').lower() == BROADCAST_GENRE.lower() for genre in update.get('genre')):
                raise SuperdeskApiError.badRequestError("Broadcast cannot be a update story !")

            if original.get('profile') and original.get('profile') != update.get('profile'):
                raise SuperdeskApiError.badRequestError("Rewrite item content profile does "
                                                        "not match with Original item.")

    def _create_rewrite_article(self, original, existing_item=None, desk_id=None):
        """Creates a new story and sets the metadata from original.

        :param dict original: original story
        :param dict existing_item: existing story that is being re-written
        :return:new story
        """
        rewrite = dict()

        fields = ['family_id', 'event_id', 'flags', 'language', ASSOCIATIONS, 'extra']

        if existing_item:
            # for associate an existing file as update merge subjects
            subjects = original.get('subject', [])
            unique_subjects = {subject.get('qcode') for subject in subjects}
            rewrite['subject'] = [subject for subject in existing_item.get('subject', [])
                                  if subject.get('qcode') not in unique_subjects]
            rewrite['subject'].extend(subjects)
        else:
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
                    'target_regions', 'target_types', 'target_subscribers'
                ]

            fields.extend(extended_fields)

        for field in fields:
            if original.get(field):
                rewrite[field] = original[field]

        # if the original was flagged for SMS the rewrite should not be.
        if rewrite.get('flags', {}).get('marked_for_sms', False):
            rewrite['flags']['marked_for_sms'] = False

        # SD-4595 - Default value for the update article to be set based on the system config.
        if config.RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES:
            # if True then reset to the default priority value.
            rewrite['priority'] = int(config.DEFAULT_PRIORITY_VALUE_FOR_MANUAL_ARTICLES)

        rewrite['rewrite_of'] = original[config.ID_FIELD]
        rewrite['rewrite_sequence'] = (original.get('rewrite_sequence') or 0) + 1

        if not existing_item:
            # send the document to the desk only if a new rewrite is created
            send_to(doc=rewrite, desk_id=(desk_id or original['task']['desk']), default_stage='working_stage')

            # if we are rewriting a published item then copy the body_html
            if original.get('state', '') in (CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED):
                rewrite['body_html'] = original.get('body_html', '')

        rewrite[ITEM_STATE] = CONTENT_STATE.PROGRESS
        self._set_take_key(rewrite)
        return rewrite

    def _add_rewritten_flag(self, original, rewrite):
        """Adds rewritten_by field to the existing published items.

        :param dict original: item on which rewrite is triggered
        :param dict rewrite: rewritten document
        """
        get_resource_service('published').update_published_items(original[config.ID_FIELD],
                                                                 'rewritten_by', rewrite[config.ID_FIELD])

        # modify the original item as well.
        get_resource_service(ARCHIVE).system_update(original[config.ID_FIELD],
                                                    {'rewritten_by': rewrite[config.ID_FIELD]}, original)
        app.on_archive_item_updated({'rewritten_by': rewrite[config.ID_FIELD]}, original, ITEM_REWRITE)

    def _set_take_key(self, rewrite):
        """Sets the anpa take key of the rewrite with ordinal.

        :param rewrite: rewrite story
        """
        rewrite_sequence = rewrite.get('rewrite_sequence') or 0
        if rewrite_sequence > 1:
            ordinal = self._get_ordinal(rewrite_sequence)
            rewrite['anpa_take_key'] = '{} update'.format(ordinal)
        else:
            rewrite['anpa_take_key'] = 'update'

    def _get_ordinal(self, n):
        """Returns the ordinal value of the given int."""
        if 10 <= n % 100 < 20:
            return str(n) + 'th'
        else:
            return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, "th")

    def delete(self, lookup):
        target_id = request.view_args['original_id']
        archive_service = get_resource_service(ARCHIVE)
        target = archive_service.find_one(req=None, _id=target_id)
        updates = {}

        if target.get('rewrite_of'):
            # remove the rewrite info
            ArchiveSpikeService().update_rewrite(target)

        if not target.get('rewrite_of'):
            # there is nothing to do
            raise SuperdeskApiError.badRequestError("Only updates can be unlinked!")

        if target.get('rewrite_of'):
            updates['rewrite_of'] = None

        if target.get('anpa_take_key'):
            updates['anpa_take_key'] = None

        if target.get('rewrite_sequence'):
            updates['rewrite_sequence'] = None

        if target.get('sequence'):
            updates['sequence'] = None

        updates['event_id'] = generate_guid(type=GUID_TAG)

        archive_service.system_update(target_id, updates, target)
        user = get_user(required=True)
        push_notification('item:unlink', item=target_id, user=str(user.get(config.ID_FIELD)))
        app.on_archive_item_updated(updates, target, ITEM_UNLINK)
