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
from werkzeug.wsgi import wrap_file
from .resource import Resource
from .services import BaseService
from flask import url_for, request, current_app as app

bp = superdesk.Blueprint('download_raw', __name__)
logger = logging.getLogger(__name__)


@bp.route('/download/<id>', methods=['GET'], defaults={'folder': None})
@bp.route('/download/<path:folder>/<id>', methods=['GET'])
def download_file(id, folder=None):
    filename = '{}/{}'.format(folder, id) if folder else id

    file = app.media.get(filename, 'download')
    if file:
        data = wrap_file(request.environ, file, buffer_size=1024 * 256)
        response = app.response_class(
            data,
            mimetype=file.content_type,
            direct_passthrough=True)
        response.content_length = file.length
        response.last_modified = file.upload_date
        response.headers['Content-Disposition'] = 'attachment; filename=\"export.zip\"'
        return response
    raise SuperdeskApiError.notFoundError('File not found on media storage.')


def download_url(media_id):
    return url_for('download_raw.download_file', id=media_id, _external=True)


def init_app(app):
    endpoint_name = 'download'
    app.download_url = download_url
    superdesk.blueprint(bp, app)
    service = BaseService(endpoint_name, backend=superdesk.get_backend())
    DownloadResource(endpoint_name, app=app, service=service)


class DownloadResource(Resource):
    schema = {
        'file': {'type': 'file'}
    }
    item_methods = []
