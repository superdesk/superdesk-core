# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""The Assets API to retrieve, create, update, delete the list of ``Assets``.


=====================   =================================================
**endpoint name**        'assets'
**resource title**       'Assets'
**resource url**         [GET] '/sams/assets'
**item url**             [GET] '/sams/assets/<:class:`str`>'
**schema**               :attr:`sams_client.schemas.ASSET_SCHEMA`
=====================   =================================================
"""

import logging
import magic
import superdesk
from flask import request, current_app as app
from io import BytesIO
from superdesk.errors import SuperdeskApiError
from werkzeug.wsgi import wrap_file

logger = logging.getLogger(__name__)
assets_bp = superdesk.Blueprint('sams_assets', __name__)


@assets_bp.route('/sams/assets', methods=['GET'])
def get():
    """
    Returns a list of all the registered assets
    """
    assets = assets_bp.kwargs['client'].assets.search(args=request.args.to_dict())
    return assets.json(), assets.status_code


@assets_bp.route('/sams/assets/<item_id>', methods=['GET'])
def find_one(item_id):
    """
    Uses item_id and returns the corresponding
    asset
    """
    item = assets_bp.kwargs['client'].assets.get_by_id(item_id=item_id)
    return item.json(), item.status_code


@assets_bp.route('/sams/assets/binary/<item_id>', methods=['GET'])
def get_binary(item_id):
    """
    Uses item_id and returns the corresponding
    asset binary
    """
    item = assets_bp.kwargs['client'].assets.get_binary_by_id(item_id=item_id)
    content = BytesIO(item.content)
    content_type = magic.from_buffer(content.getvalue(), mime=True)
    data = wrap_file(request.environ, content, buffer_size=1024 * 256)

    response = app.response_class(
        data,
        mimetype=content_type,
        direct_passthrough=True
    )
    return response


@assets_bp.route('/sams/assets', methods=['POST'])
def create():
    """
    Creates new Asset
    """
    files = {'binary': request.files['binary']}
    docs = request.form.to_dict()
    post_response = assets_bp.kwargs['client'].assets.create(docs=docs, files=files)
    return post_response.json(), post_response.status_code


@assets_bp.route('/sams/assets/<item_id>', methods=['DELETE'])
def delete(item_id):
    """
    Uses item_id and deletes the corresponding asset
    """
    try:
        etag = request.headers['If-Match']
    except KeyError:
        raise SuperdeskApiError.badRequestError(
            "If-Match field missing in header"
        )

    delete_response = assets_bp.kwargs['client'].assets.delete(
        item_id=item_id, headers={'If-Match': etag}
    )
    if delete_response.status_code != 204:
        return delete_response.json(), delete_response.status_code
    return '', delete_response.status_code


@assets_bp.route('/sams/assets/<item_id>', methods=['PATCH'])
def update(item_id):
    """
    Uses item_id and updates the corresponding asset
    """
    try:
        etag = request.headers['If-Match']
    except KeyError:
        raise SuperdeskApiError.badRequestError(
            "If-Match field missing in header"
        )

    files = {'binary': request.files.get('binary')}

    updates = request.form.to_dict()
    update_response = assets_bp.kwargs['client'].assets.update(
        item_id=item_id,
        updates=updates,
        headers={'If-Match': etag},
        files=files
    )
    return update_response.json(), update_response.status_code


@assets_bp.route('/sams/assets/counts', methods=['GET'], defaults={'set_ids': None})
@assets_bp.route('/sams/assets/counts/<set_ids>', methods=['GET'])
def get_assets_count(set_ids):

    counts = assets_bp.kwargs['client'].assets.get_assets_count(
        set_ids=set_ids
    )
    return counts
