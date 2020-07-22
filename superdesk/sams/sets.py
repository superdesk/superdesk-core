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
from flask import request
from superdesk.errors import SuperdeskApiError

logger = logging.getLogger(__name__)
sets_bp = superdesk.Blueprint('sams_sets', __name__)


@sets_bp.route('/sams/sets', methods=['GET'])
def get():
    """
    Returns a list of all the registered sets
    """
    sets = sets_bp.kwargs['client'].sets.search().json()
    return sets


@sets_bp.route('/sams/sets/<item_id>', methods=['GET'])
def find_one(item_id):
    """
    Uses item_id and returns the corresponding
    set
    """
    item = sets_bp.kwargs['client'].sets.get_by_id(item_id=item_id).json()
    # Handles error if cannot find item with given ID on sams client
    if item.get('code') == 404:
        return item['message'], 404
    return item


@sets_bp.route('/sams/sets', methods=['POST'])
def create():
    """
    Creates a new set
    """
    docs = [request.get_json()]
    post_response = sets_bp.kwargs['client'].sets.create(docs=docs).json()
    # Handles error if set already exists
    if post_response.get('_status') == 'ERR':
        return post_response['_error']['message'], post_response['_error']['code']
    return post_response


@sets_bp.route('/sams/sets/<item_id>', methods=['DELETE'])
def delete(item_id):
    """
    Uses item_id and deletes the corresponding set
    """
    etag = request.headers['If-Match']
    sets_bp.kwargs['client'].sets.delete(
        item_id=item_id, headers={'If-Match': etag}
    )
    return '', 204


@sets_bp.route('/sams/sets/<item_id>', methods=['PATCH'])
def update(item_id):
    """
    Uses item_id and updates the corresponding set
    """
    etag = request.headers['If-Match']
    updates = request.get_json()
    update_response = sets_bp.kwargs['client'].sets.update(
        item_id=item_id,
        updates=updates,
        headers={'If-Match': etag}
    ).json()
    # Handles error returned from sams client
    if update_response.get('_status') == 'ERR':
        return update_response['_error']['message'], update_response['_error']['code']
    return '', 204
