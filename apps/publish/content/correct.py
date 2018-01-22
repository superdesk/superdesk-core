# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.media.crop import CropService
from superdesk.metadata.item import ITEM_STATE, EMBARGO, SCHEDULE_SETTINGS
from superdesk.utc import utcnow
from superdesk.text_utils import update_word_count
from apps.archive.common import set_sign_off, ITEM_OPERATION
from apps.archive.archive import update_associations
from .common import BasePublishService, BasePublishResource, ITEM_CORRECT


class CorrectPublishResource(BasePublishResource):

    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, 'correct')


class CorrectPublishService(BasePublishService):
    publish_type = 'correct'
    published_state = 'corrected'

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

    def on_update(self, updates, original):
        update_associations(updates)
        CropService().validate_multiple_crops(updates, original)
        super().on_update(updates, original)
        updates[ITEM_OPERATION] = ITEM_CORRECT
        updates['versioncreated'] = utcnow()
        updates['correction_sequence'] = original.get('correction_sequence', 1) + 1
        set_sign_off(updates, original)
        update_word_count(updates, original)

    def update(self, id, updates, original):
        CropService().create_multiple_crops(updates, original)
        super().update(id, updates, original)
