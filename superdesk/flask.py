# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

# Temporary file to proxy Flask/Quart object to legacy code
# To be removed once we completely move to new superdesk.core code

from flask import (
    request,
    url_for,
    Blueprint,
    Response,
    make_response,
    Flask,
    g,
    redirect,
    jsonify,
    render_template,
    render_template_string,
    session,
    Config,
    Request,
    abort,
    send_file,
)
from flask.json.provider import DefaultJSONProvider

__all__ = [
    "request",
    "url_for",
    "Blueprint",
    "Response",
    "make_response",
    "Flask",
    "DefaultJSONProvider",
    "g",
    "redirect",
    "jsonify",
    "render_template",
    "render_template_string",
    "session",
    "Config",
    "Request",
    "abort",
    "send_file",
]
