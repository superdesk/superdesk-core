# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""The Sets API to retrieve, create, update, delete the list of ``Sets``.


=====================   =================================================
**endpoint name**        'sets'
**resource title**       'Sets'
**resource url**         [GET] '/sams/sets'
**item url**             [GET] '/sams/sets/<:class:`str`>'
**schema**               :attr:`sams_client.schemas.SET_SCHEMA`
=====================   =================================================
"""

import logging
import superdesk
from flask import request, current_app as app
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from apps.auth import get_auth, get_user_id
from .client import get_sams_client

logger = logging.getLogger(__name__)
sets_bp = superdesk.Blueprint("sams_sets", __name__)


@sets_bp.route("/sams/sets", methods=["GET"])
def get():
    """
    Returns a list of all the registered sets
    """
    sets = get_sams_client().sets.search()
    return sets.json(), sets.status_code


@sets_bp.route("/sams/sets/<item_id>", methods=["GET"])
def find_one(item_id):
    """
    Uses item_id and returns the corresponding
    set
    """
    item = get_sams_client().sets.get_by_id(item_id=item_id)
    return item.json(), item.status_code


@sets_bp.route("/sams/sets", methods=["POST"])
def create():
    """
    Creates new sets
    """
    docs = request.get_json()
    post_response = get_sams_client().sets.create(docs=docs, external_user_id=get_user_id(True))
    if post_response.status_code == 201:
        push_notification(
            "sams:set:created",
            item_id=post_response.json()["_id"],
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            _etag=post_response.json()["_etag"],
            extension="sams",
        )
    return post_response.json(), post_response.status_code


@sets_bp.route("/sams/sets/<item_id>", methods=["DELETE"])
def delete(item_id):
    """
    Uses item_id and deletes the corresponding set
    """
    try:
        etag = request.headers["If-Match"]
    except KeyError:
        raise SuperdeskApiError.badRequestError("If-Match field missing in header")

    delete_response = get_sams_client().sets.delete(item_id=item_id, headers={"If-Match": etag})
    if delete_response.status_code != 204:
        return delete_response.json(), delete_response.status_code
    if delete_response.status_code == 204:
        remove_set_restriction_from_desks(item_id)
        push_notification(
            "sams:set:deleted",
            item_id=item_id,
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            extension="sams",
        )
    return "", delete_response.status_code


def remove_set_restriction_from_desks(set_id_to_remove: str):
    """
    Removes the provided Set from "sams_settings.sets" from all Desks
    """

    desk_service = superdesk.get_resource_service("desks")
    desks_db = app.data.mongo.pymongo("desks").db["desks"]

    # Use pymongo directly as this query doesn't work through services
    for desk in desks_db.find({"sams_settings.allowed_sets": set_id_to_remove}):
        desk["sams_settings"]["allowed_sets"] = [
            set_id for set_id in desk["sams_settings"]["allowed_sets"] if set_id != set_id_to_remove
        ]
        desk_service.patch(id=desk["_id"], updates={"sams_settings": desk["sams_settings"]})


@sets_bp.route("/sams/sets/<item_id>", methods=["PATCH"])
def update(item_id):
    """
    Uses item_id and updates the corresponding set
    """
    try:
        etag = request.headers["If-Match"]
    except KeyError:
        raise SuperdeskApiError.badRequestError("If-Match field missing in header")

    updates = request.get_json()
    update_response = get_sams_client().sets.update(item_id=item_id, updates=updates, headers={"If-Match": etag})
    if update_response.status_code == 200:
        push_notification(
            "sams:set:updated",
            item_id=update_response.json()["_id"],
            user_id=get_user_id(True),
            session_id=get_auth()["_id"],
            _etag=update_response.json()["_etag"],
            extension="sams",
        )
    return update_response.json(), update_response.status_code
