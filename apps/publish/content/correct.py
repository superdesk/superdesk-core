# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service, editor_utils, config
from superdesk.media.crop import CropService
from superdesk.metadata.item import (ITEM_STATE, EMBARGO, SCHEDULE_SETTINGS,
                                     CONTENT_STATE, ASSOCIATIONS, PROCESSED_FROM)
from superdesk.utc import utcnow
from superdesk.text_utils import update_word_count
from apps.archive.common import set_sign_off, ITEM_OPERATION, get_user
from apps.archive.archive import flush_renditions
from .common import BasePublishService, BasePublishResource, ITEM_CORRECT
from superdesk.emails import send_translation_changed
from superdesk.activity import add_activity
from flask import g, current_app as app
from apps.tasks import send_to
from apps.auth import get_user_id


def send_translation_notifications(original):
    translated_items = get_resource_service('published').find({
        'translation_id': original.get('guid'),
        'last_published_version': True
    })

    user_ids = set()
    for translated_item in translated_items:
        if translated_item.get('item_id') == original.get('_id'):
            changed_article = translated_item
            continue
        user_ids.add(translated_item.get('original_creator'))
        user_ids.add(translated_item.get('version_creator'))

    if len(user_ids) == 0 or changed_article is None:
        return

    add_activity('translated:changed', '', resource=None, item=changed_article, notify=user_ids)

    recipients = []
    for user_id in user_ids:
        user = get_resource_service('users').find_one(req=None, _id=user_id)
        if user is not None and user.get('email', None) is not None:
            recipients.append(user.get('email'))

    if len(recipients) == 0:
        return

    username = g.user.get('display_name') or g.user.get('username')
    send_translation_changed(username, changed_article, recipients)


class CorrectPublishResource(BasePublishResource):

    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, 'correct')


class CorrectPublishService(BasePublishService):
    publish_type = 'correct'
    published_state = 'corrected'
    item_operation = ITEM_CORRECT

    def set_state(self, original, updates):
        updates[ITEM_STATE] = self.published_state

        if original.get(EMBARGO) or updates.get(EMBARGO):
            # embargo time elapsed
            utc_embargo = updates.get(SCHEDULE_SETTINGS, {}).get('utc_{}'.format(EMBARGO)) or \
                original.get(SCHEDULE_SETTINGS, {}).get('utc_{}'.format(EMBARGO))
            if utc_embargo and utc_embargo < utcnow():
                # remove embargo information. so the next correction is without embargo.
                updates[EMBARGO] = None
                super().set_state(original, updates)
        else:
            super().set_state(original, updates)

    def _create_correction_article(self, original, updates=None):
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
        print(fields)
        # if the field is present in updates or original, add it and delete it from updates
        for field in fields:
            if original.get(field) or updates.get(field):
                correction[field] = updates.get(field, original.get(field))

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
        correction['operation'] = 'correction'
        return correction

    def on_update(self, updates, original):
        CropService().validate_multiple_crops(updates, original)
        super().on_update(updates, original)

        # create a new correction item with the updates values.
        correction = self._create_correction_article(original, updates=updates)
        correction_ids = get_resource_service('archive').post([correction])

        updates[ITEM_OPERATION] = self.item_operation
        updates['versioncreated'] = utcnow()
        updates[ITEM_STATE] = CONTENT_STATE.BEING_CORRECTED
        updates['correction_by'] = correction_ids[0]

        set_sign_off(updates, original)
        update_word_count(updates, original)
        flush_renditions(updates, original)

    def update(self, id, updates, original):
        editor_utils.generate_fields(updates)
        get_resource_service('archive')._handle_media_updates(updates, original, get_user())
        super().update(id, updates, original)

    def on_updated(self, updates, original):
        super().on_updated(updates, original)
        send_translation_notifications(original)
