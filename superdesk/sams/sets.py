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
from .base_service import BaseService
from sams_client.schemas import SET_SCHEMA
from superdesk.errors import SuperdeskApiError
from superdesk.resource import Resource
from superdesk.utils import ListCursor

logger = logging.getLogger(__name__)


class SetsResource(Resource):
    """Resource instance for Sets
    **schema** =
        ``state`` *string*
        ``name`` *string*
        ``description`` *string*
        ``destination_name`` *string*
        ``destination_config`` *dict*
    """
    endpoint_name = 'sets'
    resource_title = 'Sets'

    url = 'sams/sets'
    item_url = r'regex("[a-zA-Z0-9]+")'

    item_methods = ['GET', 'PATCH', 'DELETE']
    resource_methods = ['GET', 'POST']
    privileges = {'POST': 'sets', 'PATCH': 'sets', 'DELETE': 'sets'}

    schema = SET_SCHEMA


class SetsService(BaseService):
    """
    Service for proxy to sams sets endpoints
    """
    def extract_item(self, arg):
        """
        Method to remove fields from a dictionary type item
        """
        fields_to_remove = ['_created', '_updated', '_etag']
        return dict(
            (key, arg[key]) for key in set(arg.keys()) - set(fields_to_remove)
        )

    def get(self, req, **lookup):
        """
        Returns a list of all the registered sets
        """
        sets = self.client.sets.search().json()
        items = list(map(
            lambda item: self.parse_date(item),
            sets['_items']
        ))
        return ListCursor(items)

    def find_one(self, req, **lookup):
        """
        Uses ``_id`` or ``name`` in the lookup and returns the corresponding
        set
        """
        # For delete and update find_one gets called with
        # key as '_id' in lookup
        # For create find_one gets called with key as 'name' in lookup
        name = lookup.get('_id', lookup.get('name'))
        item = self.client.sets.get_by_id(item_id=name).json()
        # Handles error if cannot find item with given ID on sams client
        if item.get('code') == 404:
            if lookup.get('name'):      # returns None in case of create
                return None
            raise SuperdeskApiError.notFoundError(item['message'])
        return self.parse_date(item)

    def create(self, docs, **lookup):
        """
        Uses docs from arguments and creates a new set
        """
        docs[0] = self.extract_item(docs[0])
        post_response = self.client.sets.create(docs=docs).json()
        # Handles error if set already exists
        if post_response.get('_status') == 'ERR':
            raise SuperdeskApiError.badRequestError(
                message=post_response['_error']['message'],
                payload=post_response['_issues']
            )
        return [post_response['_id']]

    def delete(self, lookup):
        """
        Uses ``_id`` in the lookup and deletes the corresponding set
        """
        name = lookup['_id']
        item = self.client.sets.get_by_id(item_id=name).json()
        self.client.sets.delete(
            item_id=name, headers={'If-Match': item['_etag']}
        )

    def update(self, id, updates, original):
        """
        Uses id and updates from arguments and updates the corresponding set
        """
        updates = self.extract_item(updates)
        self.client.sets.update(
            item_id=id,
            updates=updates,
            headers={'If-Match': original['_etag']}
        )
