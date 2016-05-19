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
import io
import logging
import os
import pstats
import re
from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService

from flask import current_app as app


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
    LINE_FIELDS = {
        1: 'ncalls',
        2: 'tottime',
        3: 'percall',
        4: 'cumtime',
        5: 'percall_cumtime',
        6: 'filename_lineno',
        7: 'func_name'
    }
    LINE_REGEX = r'\s*([\d\/]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([^\(]+)\(([^\)]+)\)$'
    DEFAULT_SORT = 'cumulative'
    SORT_FIELDS = [
        'calls', 'cumulative', 'cumtime', 'file', 'filename', 'module', 'ncalls', 'pcalls',
        'line', 'name', 'nfl', 'stdname', 'time', 'tottime'
    ]

    def delete(self, lookup):
        """
        Resets the profiling data.
        """
        profile.disable()
        if app.config.get('PROFILING_DATA_FILE'):
            profiling_file = app.config['PROFILING_DATA_FILE']
            try:
                os.unlink(profiling_file)
                profile.dump_stats(profiling_file)
            except FileNotFoundError:
                profile.dump_stats(profiling_file)
            except:
                logger.warning('Unable to writin profiling file')
        profile.enable()
        return True

    def get(self, req, lookup):
        """
        Returns the profiling data sorted by given field(s). (see SORT_FIELDS)
        A profile line contains the fields listed in LINE_FIELDS.
        """
        profile_output = io.StringIO()
        sort_fields = self._get_sort(req)
        if os.path.isfile(app.config.get('PROFILING_DATA_FILE')):
            stats_from = app.config['PROFILING_DATA_FILE']
        else:
            stats_from = profile
        ps = pstats.Stats(stats_from, stream=profile_output).sort_stats(*sort_fields)
        ps.print_stats()
        lines = profile_output.getvalue().splitlines(True)
        profile_lines = []
        for line in lines:
            processed_line = self._process_line(line)
            if processed_line:
                profile_lines.append(processed_line)
        profile_res = {'sort': sort_fields, 'data': profile_lines}
        return Cursor([profile_res])

    def _process_line(self, line):
        """
        Reads from a text line the profiling fields into a dictionary.
        """
        match = re.search(self.LINE_REGEX, line)
        if match:
            return {self.LINE_FIELDS[index]: match.group(index) for index in range(1, 8)}

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
