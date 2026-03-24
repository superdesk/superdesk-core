# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.tests.environment import *  # noqa
from superdesk.tests import environment as _base_env

import json
import os
import re
import responses as responses_lib
from urllib.parse import urlparse, parse_qs

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "steps", "fixtures")


def _load_fixture(filename):
    with open(os.path.join(_FIXTURES_DIR, filename)) as f:
        return json.load(f)


def _geonames_search_callback(request):
    params = parse_qs(urlparse(request.url).query)
    feature_classes = {fc.upper() for fc in params.get("featureClass", [])}
    items = []
    if "P" in feature_classes:
        items.extend(_load_fixture("geonames_search_P.json"))
    if "A" in feature_classes:
        items.extend(_load_fixture("geonames_search_A.json"))
    body = json.dumps({"totalResultsCount": len(items), "geonames": items})
    return (200, {}, body)


def before_scenario(context, scenario):
    _base_env.before_scenario(context, scenario)
    if "mock_geonames" in scenario.tags:
        rsps = responses_lib.RequestsMock(assert_all_requests_are_fired=False)
        rsps.add_callback(
            responses_lib.GET,
            re.compile(r"https?://[^/]*geonames\.org/search"),
            callback=_geonames_search_callback,
            content_type="application/json",
        )
        rsps.start()
        context._geonames_rsps = rsps


def after_scenario(context, scenario):
    if hasattr(context, "_geonames_rsps"):
        context._geonames_rsps.stop()
        context._geonames_rsps.reset()
        context.__dict__.pop("_geonames_rsps", None)
    _base_env.after_scenario(context, scenario)
