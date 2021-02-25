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
from superdesk.upload import get_upload_as_data_uri
from flask import current_app as app


bp = superdesk.Blueprint("assets", __name__)


@bp.route("/assets/<path:media_id>", methods=["GET"])
def prod_get_upload_as_data_uri(media_id):
    return get_upload_as_data_uri(media_id)


def upload_url(media_id, view=prod_get_upload_as_data_uri):
    return "{}/{}".format(app.config.get("MEDIA_PREFIX").rstrip("/"), media_id)


def init_app(app) -> None:
    superdesk.blueprint(bp, app)
    app.upload_url = upload_url
