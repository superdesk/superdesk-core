# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
"""Assets module"""

import superdesk
import bson.errors

from werkzeug.wsgi import wrap_file
from flask import request, current_app as app
from content_api.errors import FileNotFoundError
from superdesk import get_resource_service
from superdesk.upload import upload_url as _upload_url

bp = superdesk.Blueprint("assets", __name__)
cache_for = 3600 * 24 * 7  # 7 days cache


@bp.route("/assets/<path:media_id>", methods=["GET"])
def get_media_streamed(media_id):
    if not app.auth.authorized([], "assets", "GET"):
        return app.auth.authenticate()
    try:
        media_file = app.media.get(media_id, "upload")
    except bson.errors.InvalidId:
        media_file = None
    if media_file:
        data = wrap_file(request.environ, media_file, buffer_size=1024 * 256)
        response = app.response_class(data, mimetype=media_file.content_type, direct_passthrough=True)
        response.content_length = media_file.length
        response.last_modified = media_file.upload_date
        response.set_etag(media_file.md5)
        response.cache_control.max_age = cache_for
        response.cache_control.s_max_age = cache_for
        response.cache_control.public = True
        response.make_conditional(request)
        response.headers["Content-Disposition"] = "inline"
        get_resource_service("api_audit").audit_item({"type": "asset", "uri": request.url}, media_id)
        return response
    raise FileNotFoundError("File not found on media storage.")


def upload_url(media_id):
    return _upload_url(media_id, view="assets.get_media_streamed")


def init_app(app):
    superdesk.blueprint(bp, app)
    app.upload_url = upload_url
