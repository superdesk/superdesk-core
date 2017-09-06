# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import copy
from datetime import timedelta
import re

from eve.utils import config
from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService


class SystemSettingsService(BaseService):

    def on_create(self, docs):
        for doc in docs:
            self._validate_value(doc)

    def on_update(self, updates, original):
        updated = copy.deepcopy(original)
        updated.update(updates)
        self._validate_value(updated)

    def on_replace(self, document, original):
        self._validate_value(document)

    def _validate_value(self, doc):
        if doc['type'] == 'string' and type(doc['value'] != 'string'):
            raise SuperdeskApiError.badRequestError('Property \'' + doc[config.ID_FIELD] + '\' must be a string.')
        if doc['type'] == 'integer' and not doc['value'].isdigit():
            raise SuperdeskApiError.badRequestError('Property \'' + doc[config.ID_FIELD] + '\' must be an integer.')
        if doc['type'] == 'timedelta':
            self.validate_timedelta(doc)

    def validate_timedelta(self, doc):
        message = 'Property \'%s\' must be a time delta value in the format ' \
            '\'xxd xxh xxm xxs\', where x represents a digit.' % doc[config.ID_FIELD]

        res = re.search('(\d{1,2}d)?\s*(\d{1,2}h)?\s*(\d{1,2}m)?\s*(\d{1,2}s)?', doc['value'])
        if not res:
            raise SuperdeskApiError.badRequestError(message)
        days, hours, minutes, seconds = res.group(1, 2, 3, 4)
        days = int(days[0:-1]) if days else 0
        hours = int(hours[0:-1]) if hours else 0
        minutes = int(minutes[0:-1]) if minutes else 0
        seconds = int(seconds[0:-1]) if seconds else 0
        if days == 0 and hours == 0 and minutes == 0 and seconds == 0:
            raise SuperdeskApiError.badRequestError(message)
        if hours >= 24 or minutes >= 60 or seconds >= 60:
            raise SuperdeskApiError.badRequestError(message)

        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
