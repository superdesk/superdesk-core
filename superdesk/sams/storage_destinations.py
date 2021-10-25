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


=====================   =======================================================
**endpoint name**        'storage_destinations'
**resource title**       'Destinations'
**resource url**         [GET] '/sams/destinations'
**item url**             [GET] '/sams/destinations/<:class:`str`>'
**schema**               :attr:`sams_client.schemas.destinationSchema`
=====================   =======================================================
"""

import logging
import superdesk
from .client import get_sams_client

logger = logging.getLogger(__name__)
destinations_bp = superdesk.Blueprint("sams_destinations", __name__)


@destinations_bp.route("/sams/destinations", methods=["GET"])
def get():
    """
    Returns a list of all the registered storage destinations
    """
    destinations = get_sams_client().destinations.search()
    return destinations.json(), destinations.status_code


@destinations_bp.route("/sams/destinations/<item_id>", methods=["GET"])
def find_one(item_id):
    """
    Uses item_id and returns the destination
    name and provider name of the respective storage destination
    """
    item = get_sams_client().destinations.get_by_id(item_id=item_id)
    return item.json(), item.status_code
