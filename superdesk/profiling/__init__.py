# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import io
import logging
import pstats
import re

from flask_babel import lazy_gettext
from superdesk import get_resource_service
import superdesk

from flask import current_app as app

from superdesk.profiling.resource import ProfilingResource
from superdesk.profiling.service import ProfilingService, profile


logger = logging.getLogger(__name__)


def init_app(app) -> None:
    if app.config.get("ENABLE_PROFILING"):
        endpoint_name = "profiling"
        service = ProfilingService(endpoint_name, backend=superdesk.get_backend())
        ProfilingResource(endpoint_name, app=app, service=service)

        superdesk.privilege(
            name="profiling",
            label=lazy_gettext("Profiling Service"),
            description=lazy_gettext("User can read profiling data."),
        )

        profile.enable()


class ProfileManager:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        if app.config.get("ENABLE_PROFILING"):
            profile.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        if app.config.get("ENABLE_PROFILING"):
            profile.disable()
            dump_stats(profile, self.name)


def dump_stats(profile, name):
    """Dump the profiling stats

    :param cProfile.Profile profile: the profile object
    :param string name: the name that identifies the profile
    """
    profile_output = io.StringIO()
    ps = pstats.Stats(profile, stream=profile_output).sort_stats("cumulative")
    ps.print_stats()
    lines = profile_output.getvalue().splitlines(True)
    profile_lines = []
    for line in lines:
        processed_line = _process_line(line)
        if processed_line:
            profile_lines.append(processed_line)
    profile_rec = get_resource_service("profiling").find_one(req=None, _id=name)
    if profile_rec:
        get_resource_service("profiling").patch(name, {"profiling_data": profile_lines})
    else:
        get_resource_service("profiling").post([{"name": name, "profiling_data": profile_lines}])


def _process_line(line):
    """
    Reads from a text line the profiling fields into a dictionary.
    """
    LINE_FIELDS = {
        1: "ncalls",
        2: "tottime",
        3: "percall",
        4: "cumtime",
        5: "percall_cumtime",
        6: "filename_lineno",
        7: "func_name",
    }
    LINE_REGEX = r"\s*([\d\/]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([^\(]+)\(([^\)]+)\)$"

    match = re.search(LINE_REGEX, line)
    if match:
        return {LINE_FIELDS[index]: match.group(index) for index in range(1, 8)}
