# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from os.path import basename
import re
from yarl import URL
from aioresponses import CallbackResult

from .http_mocks import mock_http


def item_request(url: URL, params: dict, **kwargs) -> CallbackResult:
    try:
        fixtures = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../../tests/io/fixtures")
        if "channel" in params:
            file = os.path.join(fixtures, params["channel"])
        else:
            file = os.path.join(fixtures, params["id"].replace(":", "_version_"))
        with open(file, "rb") as stored_response:
            content = stored_response.read()
            return CallbackResult(status=200, body=content, content_type="application/xml")
    except Exception:
        return CallbackResult(status=404)


def content_request(url: URL, **kwargs) -> CallbackResult:
    try:
        fixtures = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../../tests/io/fixtures")
        file = os.path.join(fixtures, basename(url.path))
        with open(file, "rb") as stored_response:
            content = stored_response.read()
            return CallbackResult(status=200, body=content, content_type="application/xml")
    except Exception:
        return CallbackResult(status=404)


def setup_reuters_mock(context):
    mock = mock_http(context)
    mock.get(
        re.compile(r"https://commerce\.reuters\.com/rmd/rest/xml/login.*"),
        status=200,
        body='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><authToken>fake_token</authToken>',
        content_type="application/xml",
        repeat=True,
    )
    mock.get(
        re.compile(r"^http://rmb\.reuters\.com/rmd/rest/xml/item.*"),
        callback=item_request,
        repeat=True,
    )
    mock.get(
        re.compile(r"^http://content\.reuters\.com.*"),
        callback=content_request,
        repeat=True,
    )
