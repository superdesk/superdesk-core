# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Download module"""
import logging
import superdesk
from superdesk.errors import SuperdeskApiError
from superdesk.auth.decorator import blueprint_auth
from .resource import Resource
from .services import BaseService
from superdesk.core import get_current_app, get_config
from superdesk.flask import request, Blueprint, url_for
from superdesk.storage.superdesk_file import generate_response_for_file, get_file_request_range

bp = Blueprint("download_raw", __name__)
logger = logging.getLogger(__name__)


@bp.route("/download/<id>", methods=["GET"], defaults={"folder": None})
@bp.route("/download/<path:folder>/<id>", methods=["GET"])
@blueprint_auth()
async def download_file(id, folder=None):
    filename = "{}/{}".format(folder, id) if folder else id
    app = get_current_app()

    begin, end = get_file_request_range(request.range)
    file = await app.media.get_async(filename, "download", begin=begin, end=end)
    if file:
        return await generate_response_for_file(file, content_disposition='attachment; filename="export.zip"')
    raise SuperdeskApiError.notFoundError("File not found on media storage.")


def download_url(media_id):
    prefered_url_scheme = get_config(str, "PREFERRED_URL_SCHEME", "http")
    return url_for("download_raw.download_file", id=media_id, _external=True, _scheme=prefered_url_scheme)


def init_app(app) -> None:
    endpoint_name = "download"
    app.download_url = download_url
    superdesk.blueprint(bp, app)
    service = BaseService(endpoint_name, backend=superdesk.get_backend())
    DownloadResource(endpoint_name, app=app, service=service)


class DownloadResource(Resource):
    schema = {"file": {"type": "file"}}
    item_methods = []
