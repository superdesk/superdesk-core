# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import cProfile
import logging
from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService

from eve.utils import config


logger = logging.getLogger(__name__)

profile = cProfile.Profile()


class Cursor:
    """
    Simulate pymongo Cursor for retuned results
    """

    def __init__(self, iterable):
        self.iterable = iterable

    def __iter__(self):
        return self.iterable.__iter__()

    def __getitem__(self, index):
        return self.iterable[index]

    def __next__(self):
        yield self.iterable.__next__()

    def count(self, with_limit_and_skip=False):
        return len(self.iterable)


class ProfilingService(BaseService):
    """
    Allows reading of the profiling data
    """

    def on_create(self, docs):
        for doc in docs:
            doc[config.ID_FIELD] = doc['name']

    def delete(self, lookup):
        """
        Resets the profiling data.
        """
        try:
            profile.disable()
            from superdesk.profiling import dump_stats
            dump_stats(profile, 'rest')
        finally:
            profile.enable()
        return True

    def _get_sort(self, req):
        """
        Returns the sort fields in a list based on the received request.
        """
        if not req or not req.sort:
            return [self.DEFAULT_SORT]
        sort_fields = req.sort.split(',')
        for field in sort_fields:
            if field not in self.SORT_FIELDS:
                raise SuperdeskApiError.badRequestError('Invalid sort field %s' % field)
        return sort_fields
