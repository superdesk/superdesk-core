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
from flask import request
from superdesk import get_resource_service, Service, config
from superdesk.metadata.item import ITEM_STATE, EMBARGO, CONTENT_STATE, CONTENT_TYPE, ITEM_TYPE, PUBLISH_STATES
from superdesk.resource import Resource, build_custom_hateoas
from apps.archive.common import CUSTOM_HATEOAS, ITEM_CREATE, ARCHIVE, BROADCAST_GENRE
from superdesk.metadata.utils import item_url
from superdesk.workflow import is_workflow_state_transition_valid
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from apps.packages.takes_package_service import TakesPackageService
from apps.tasks import send_to

logger = logging.getLogger(__name__)


class ArchiveRewriteResource(Resource):
    endpoint_name = 'archive_rewrite'
    resource_title = endpoint_name

    schema = {
        'desk_id': {'type': 'string', 'nullable': True},
        'update': {'type': 'dict', 'nullable': True}
    }

    url = 'archive/<{0}:original_id>/rewrite'.format(item_url)
    resource_methods = ['POST']
    privileges = {'POST': 'rewrite'}


class ArchiveRewriteService(Service):
    def create(self, docs, **kwargs):
        doc = docs[0] if len(docs) > 0 else {}
        original_id = request.view_args['original_id']
        update_document = doc.get('update')

        archive_service = get_resource_service(ARCHIVE)
        original = archive_service.find_one(req=None, _id=original_id)
        self._validate_rewrite(original, update_document)

        digital = TakesPackageService().get_take_package(original)
        rewrite = self._create_rewrite_article(original, digital, new_file=(update_document is None))

        if update_document:
            # process the existing story
            archive_service.patch(update_document[config.ID_FIELD], rewrite)
            rewrite[config.ID_FIELD] = update_document[config.ID_FIELD]
            ids = [update_document[config.ID_FIELD]]
        else:
            # create a new story as update
            ids = archive_service.post([rewrite])
            build_custom_hateoas(CUSTOM_HATEOAS, rewrite)

        self._add_rewritten_flag(original, digital, rewrite)
        get_resource_service('archive_broadcast').on_broadcast_master_updated(ITEM_CREATE,
                                                                              item=original,
                                                                              rewrite_id=ids[0])
        return [rewrite]

    def _validate_rewrite(self, original, update):
        """
        Validates the article to be rewritten
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

        if not TakesPackageService().is_last_takes_package_item(original):
            raise SuperdeskApiError.badRequestError(message="Only last take of the package can be rewritten.")

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

    def _create_rewrite_article(self, original, digital, new_file=True):
        """
        Creates a new story and sets the metadata from original and digital
        :param original: original story
        :param digital: digital version of the story
        :param new_file: False if an existing file is used as update
        :return:new story
        """
        rewrite = dict()

        fields = ['family_id', 'event_id', 'flags']

        if new_file:
            fields.extend(['abstract', 'anpa_category', 'pubstatus', 'slugline', 'urgency',
                           'subject', 'priority', 'byline', 'dateline', 'headline', 'place',
                           'genre', 'body_footer', 'company_codes', 'keywords'])

        for field in fields:
                if original.get(field):
                    rewrite[field] = original[field]

        if digital:  # check if there's digital
            rewrite['rewrite_of'] = digital[config.ID_FIELD]
        else:  # if not use original's id
            rewrite['rewrite_of'] = original[config.ID_FIELD]

        if new_file:
            # send the document to the desk only if a new rewrite is created
            send_to(doc=rewrite, desk_id=original['task']['desk'], default_stage='working_stage')

        rewrite[ITEM_STATE] = CONTENT_STATE.PROGRESS
        self._set_take_key(rewrite, original.get('event_id'))
        return rewrite

    def _add_rewritten_flag(self, original, digital, rewrite):
        """
        Adds rewritten_by field to the existing published items.
        :param dict original: item on which rewrite is triggered
        :param dict digital: digital item
        :param dict rewrite: rewritten document
        """
        get_resource_service('published').update_published_items(original[config.ID_FIELD],
                                                                 'rewritten_by', rewrite[config.ID_FIELD])
        if digital:
            # update the rewritten_by for digital
            get_resource_service('published').update_published_items(digital[config.ID_FIELD], 'rewritten_by',
                                                                     rewrite[config.ID_FIELD])
            get_resource_service(ARCHIVE).system_update(digital[config.ID_FIELD],
                                                        {'rewritten_by': rewrite[config.ID_FIELD]}, digital)

        # modify the original item as well.
        get_resource_service(ARCHIVE).system_update(original[config.ID_FIELD],
                                                    {'rewritten_by': rewrite[config.ID_FIELD]}, original)

    def _clear_rewritten_flag(self, event_id, rewrite_id, rewrite_field):
        """
        Clears rewritten_by or rewrite_of field from the existing published and archive items
        :param str event_id: event id of the document
        :param str rewrite_id: rewrite id of the document
        :param str rewrite_field: field name 'rewrite_of' or 'rewritten_by'
        """
        publish_service = get_resource_service('published')
        archive_service = get_resource_service(ARCHIVE)

        published_rewritten_stories = publish_service.get_rewritten_items_by_event_story(event_id,
                                                                                         rewrite_id, rewrite_field)
        processed_items = set()
        for doc in published_rewritten_stories:
            doc_id = doc.get(config.ID_FIELD)
            publish_service.update_published_items(doc_id, rewrite_field, None)
            if doc_id not in processed_items:
                # clear the flag from the archive as well.
                archive_item = archive_service.find_one(req=None, _id=doc_id)
                archive_service.system_update(doc_id, {rewrite_field: None}, archive_item)
                processed_items.add(doc_id)

    def _set_take_key(self, rewrite, event_id):
        """
        Sets the anpa take key of the rewrite with ordinal
        :param rewrite: rewrite story
        :param event_id: event id
        """
        published_digital_stories = get_resource_service('published'). \
            get_rewritten_take_packages_per_event(event_id)

        digital_count = published_digital_stories.count()
        if digital_count > 0:
            ordinal = self._get_ordinal(digital_count + 1)
            rewrite['anpa_take_key'] = '{} update'.format(ordinal)
        else:
            rewrite['anpa_take_key'] = 'update'

    def _get_ordinal(self, n):
        """ Returns the ordinal value of the given int """
        if 10 <= n % 100 < 20:
            return str(n) + 'th'
        else:
            return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, "th")
