# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from superdesk.core import get_app_config, get_current_app
from superdesk.flask import Blueprint, request
from superdesk.upload import _get_upload_as_data_uri


bp = Blueprint("assets", __name__)


@bp.route("/assets/<path:media_id>", methods=["GET"])
async def prod_get_upload_as_data_uri(media_id):
    app = get_current_app()
    if app.auth and not app.auth.authorized([], "archive", request.method):
        return app.auth.authenticate()
    return await _get_upload_as_data_uri(media_id)


def upload_url(media_id, view=prod_get_upload_as_data_uri):
    return "{}/{}".format(get_app_config("MEDIA_PREFIX").rstrip("/"), media_id)


def init_app(app) -> None:
    superdesk.blueprint(bp, app)
    app.upload_url = upload_url
