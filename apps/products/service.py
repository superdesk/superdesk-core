# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from superdesk.services import BaseService
from eve.utils import ParsedRequest
from superdesk.errors import SuperdeskApiError


class ProductsService(BaseService):
    def on_delete(self, doc):
        # Check if any subscriber is using the product
        req = ParsedRequest()
        lookup = {'products': {'$in': [doc['_id']]}}
        subscribers = list(get_resource_service('subscribers').get(req=req, lookup=lookup))
        if len(subscribers) > 0:
            names = [s['name'] for s in subscribers]
            raise SuperdeskApiError.badRequestError(
                message="Product is used by the subscriber(s): {}".format(", ".join(names)))
