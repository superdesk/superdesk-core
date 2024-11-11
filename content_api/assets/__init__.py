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

from superdesk.core import get_current_app
from superdesk.flask import request, Blueprint
from content_api.errors import FileNotFoundError
from superdesk import get_resource_service
from superdesk.upload import upload_url as _upload_url
from superdesk.storage.superdesk_file import generate_response_for_file

bp = Blueprint("assets", __name__)


@bp.route("/assets/<path:media_id>", methods=["GET"])
async def get_media_streamed(media_id):
    app = get_current_app()
    if not app.auth.authorized([], "assets", "GET"):
        return app.auth.authenticate()
    try:
        media_file = app.media.get(media_id, "upload")
        if not media_file:
            media_id = media_id.split(".")[0]
            media_file = app.media.get(media_id, "upload")
    except bson.errors.InvalidId:
        media_file = None
    if media_file:
        get_resource_service("api_audit").audit_item({"type": "asset", "uri": request.url}, media_id)
        return await generate_response_for_file(
            media_file, cache_for=3600 * 24 * 7, content_disposition="inline"  # 7 days cache
        )
    raise FileNotFoundError("File not found on media storage.")


def upload_url(media_id):
    return _upload_url(media_id, view="assets.get_media_streamed")


def init_app(app) -> None:
    superdesk.blueprint(bp, app)
    app.upload_url = upload_url
