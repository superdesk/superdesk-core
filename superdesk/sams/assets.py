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

import ast
import logging
import superdesk
from flask import request
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from .utils import get_file_from_sams
from superdesk.storage.superdesk_file import generate_response_for_file
from apps.auth import get_auth, get_user_id
from .client import get_sams_client

logger = logging.getLogger(__name__)
assets_bp = superdesk.Blueprint("sams_assets", __name__)


@assets_bp.route("/sams/assets", methods=["GET"])
def get():
    """
    Returns a list of all the registered assets
    """
    assets = get_sams_client().assets.search(params=request.args.to_dict())
    return assets.json(), assets.status_code


@assets_bp.route("/sams/assets/<item_id>", methods=["GET"])
def find_one(item_id):
    """
    Uses item_id and returns the corresponding
    asset
    """
    item = get_sams_client().assets.get_by_id(item_id=item_id)
    return item.json(), item.status_code


@assets_bp.route("/sams/assets/binary/<item_id>", methods=["GET"])
def get_binary(item_id):
    """
    Uses item_id and returns the corresponding
    asset binary
    """
    file = get_file_from_sams(get_sams_client(), item_id)
    return generate_response_for_file(file)


@assets_bp.route("/sams/assets", methods=["POST"])
def create():
    """
    Creates new Asset
    """
    files = {"binary": request.files["binary"]}
    docs = request.form.to_dict()
    post_response = get_sams_client().assets.create(docs=docs, files=files, external_user_id=get_user_id(True))
    if post_response.status_code == 201:
        push_notification(
            "sams:asset:created",
            item_id=post_response.json()["_id"],
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            _etag=post_response.json()["_etag"],
            extension="sams",
        )
    return post_response.json(), post_response.status_code


@assets_bp.route("/sams/assets/<item_id>", methods=["DELETE"])
def delete(item_id):
    """
    Uses item_id and deletes the corresponding asset
    """
    try:
        etag = request.headers["If-Match"]
    except KeyError:
        raise SuperdeskApiError.badRequestError("If-Match field missing in header")

    delete_response = get_sams_client().assets.delete(item_id=item_id, headers={"If-Match": etag})
    if delete_response.status_code != 204:
        return delete_response.json(), delete_response.status_code
    if delete_response.status_code == 204:
        push_notification(
            "sams:asset:deleted",
            item_id=item_id,
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            extension="sams",
        )
    return "", delete_response.status_code


@assets_bp.route("/sams/assets/<item_id>", methods=["PATCH"])
def update(item_id):
    """
    Uses item_id and updates the corresponding asset
    """
    try:
        etag = request.headers["If-Match"]
    except KeyError:
        raise SuperdeskApiError.badRequestError("If-Match field missing in header")

    if request.files.get("binary"):
        # The binary data was supplied so this must be a multipart request
        # Get the updates from the `request.form` attribute
        files = {"binary": request.files["binary"]}
        updates = request.form.to_dict()
    else:
        # Only the metadata was supplied so this must be a standard JSON request
        # Get the updates from the `request.get_json` function
        files = {}
        updates = request.get_json()

    update_response = get_sams_client().assets.update(
        item_id=item_id, updates=updates, headers={"If-Match": etag}, files=files, external_user_id=get_user_id(True)
    )
    if update_response.status_code == 200:
        push_notification(
            "sams:asset:updated",
            item_id=update_response.json()["_id"],
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            _etag=update_response.json()["_etag"],
            extension="sams",
        )
    return update_response.json(), update_response.status_code


@assets_bp.route("/sams/assets/counts", methods=["GET"], defaults={"set_ids": None})
@assets_bp.route("/sams/assets/counts/<set_ids>", methods=["GET"])
def get_assets_count(set_ids):
    set_ids = ast.literal_eval(set_ids) if set_ids else None
    counts = get_sams_client().assets.get_assets_count(set_ids=set_ids)
    return counts


@assets_bp.route("/sams/assets/compressed_binary/<asset_ids>", methods=["GET"])
def get_assets_compressed_binary(asset_ids):
    asset_ids = ast.literal_eval(asset_ids) if asset_ids else None
    zip_binary = get_sams_client().assets.get_binary_zip_by_id(item_ids=asset_ids)
    return zip_binary.content


@assets_bp.route("/sams/assets/lock/<asset_id>", methods=["PATCH"])
def lock_asset(asset_id):
    docs = request.json
    lock_asset_response = get_sams_client().assets.lock_asset(
        item_id=asset_id, external_user_id=get_user_id(True), external_session_id=get_auth()["_id"], docs=docs
    )
    if lock_asset_response.status_code == 200:
        push_notification(
            "sams:asset:lock_asset",
            item_id=asset_id,
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            _etag=lock_asset_response.json()["_etag"],
            extension="sams",
        )
    return lock_asset_response.json(), lock_asset_response.status_code


@assets_bp.route("/sams/assets/unlock/<asset_id>", methods=["PATCH"])
def unlock_asset(asset_id):
    docs = request.json
    unlock_asset_response = get_sams_client().assets.unlock_asset(
        item_id=asset_id, external_user_id=get_user_id(True), external_session_id=get_auth()["_id"], docs=docs
    )
    if unlock_asset_response.status_code == 200:
        push_notification(
            "sams:asset:unlock_asset",
            item_id=asset_id,
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            _etag=unlock_asset_response.json()["_etag"],
            extension="sams",
        )
    return unlock_asset_response.json(), unlock_asset_response.status_code


def unlock_asset_by_user(user_id, session_id):
    unlock_asset_response = get_sams_client().assets.unlock_assets_by_user(
        external_user_id=user_id, external_session_id=session_id
    )
    if unlock_asset_response.status_code == 200:
        push_notification(
            "sams:asset:session_unlock", user_id=get_user_id(True), session_id=get_auth()["_id"], extension="sams"
        )
    return unlock_asset_response.status_code


@assets_bp.route("/sams/assets/tags", methods=["GET"])
def get_assets_tags():

    search_query = request.args.to_dict().get("query")
    query = {
        "bool": {
            "must": [{"query_string": {"query": search_query, "default_field": "tags.name", "default_operator": "AND"}}]
        }
    }

    tags_response = get_sams_client().assets.get_tag_codes(query=query if search_query else search_query)
    return tags_response
