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

# Patch Quart, Asyncio to allow Flask extensions to work
# Import `signals` from flask before patching
# and add it back in (as quart_flask_patch doesn't provide flask.signals)
from flask import signals
import quart_flask_patch  # noqa
import flask

from quart import (
    request,
    url_for,
    Blueprint,
    Response,
    make_response,
    Quart as Flask,
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
from quart.cli import AppGroup
from quart.json.provider import DefaultJSONProvider


flask.signals = signals


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
    "AppGroup",
]
