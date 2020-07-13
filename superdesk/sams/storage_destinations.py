# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""The Destinations API allows to retrieve the list of ``StorageDestinations``.


=====================   =================================================================
**endpoint name**        'storage_destinations'
**resource title**       'Destinations'
**resource url**         [GET] '/sams/destinations'
**item url**             [GET] '/sams/destinations/<:class:`str`>'
**schema**               :attr:`sams_client.schemas.destinations.destinationSchema`
=====================   =================================================================
"""

from superdesk.resource import Resource
from .base_service import BaseService
from sams_client.schemas import destinationSchema
from superdesk.utils import ListCursor


class StorageDestinationsResource(Resource):

    endpoint_name = 'storage_destinations'

    url = 'sams/destinations'
    item_url = r'regex("[a-zA-Z0-9]+")'

    schema = destinationSchema

    item_methods = ['GET']
    resource_methods = ['GET']


class StorageDestinationsService(BaseService):
    def get(self, req, **lookup):
        """
        Returns a list of all the registered storage destinations
        """
        destinations = self.client.destinations.search()
        if len(destinations.json()['_items']) != 0:
            items = list(map(
                lambda item: self.to_dict(item),
                destinations.json()['_items']
            ))
            return ListCursor(items)
        return ListCursor(destinations.json()['_items'])

    def find_one(self, req, **lookup):
        """
        Uses ``_id`` in the lookup and returns the destination
        name and provider name of the respective storage destination
        """
        name = lookup['_id']
        destination = self.client.destinations.get_by_id(name)
        return self.to_dict(destination.json())
