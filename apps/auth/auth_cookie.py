# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import timedelta
from flask import make_response, current_app as app, request, g
from superdesk import Blueprint
from superdesk.utc import utcnow

auth_cookie_bp = Blueprint("auth_cookie_bp", __name__)


@auth_cookie_bp.route("/auth_cookie", methods=["POST", "OPTIONS"])
def get_auth_test_post():
    client_url: str = app.config["CLIENT_URL"]

    response = make_response("", 200)
    response.headers.set("Access-Control-Allow-Origin", client_url)
    response.headers.set("Access-Control-Allow-Headers", "authorization")
    response.headers.set("Access-Control-Allow-Methods", "POST,OPTIONS")
    response.headers.set("Access-Control-Allow-Credentials", "true")

    if request.method != "OPTIONS":
        if app.auth.authorized([], "_blueprint", "POST"):
            response.set_cookie(
                "session_token",
                g.auth["token"],
                httponly=True,
                expires=utcnow() + timedelta(minutes=app.config["SESSION_EXPIRY_MINUTES"]),
                samesite="Strict",
                secure=client_url.startswith("https"),
            )
        else:
            response.delete_cookie("session_token")

    return response
