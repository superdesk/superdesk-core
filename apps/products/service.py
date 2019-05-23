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
from eve.utils import ParsedRequest, config
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.utils import ProductTypes
from flask_babel import _


class ProductsService(BaseService):

    def on_update(self, updates, original):
        self._validate_product_type(updates, original)

    def on_delete(self, doc):
        # Check if any subscriber is using the product
        names = get_resource_service('subscribers').get_subscriber_names({'$or': [
            {'products': {'$in': [doc['_id']]}}, {'api_products': {'$in': [doc['_id']]}}
        ]})
        if names:
            raise SuperdeskApiError.badRequestError(
                message=_("Product is used by the subscriber(s): {names}").format(names=", ".join(names)))

    def _validate_product_type(self, updates, original):
        """Validates product type field. Raises Bad Request error for following conditions:
        1. new product type is direct and product is assigned as api product.
        2. new product type is api and product is assigned as direct product.

        :param dict updates: updates to the product
        :param dict original: original of the product
        """
        if updates.get('product_type', 'both') != original.get('product_type', 'both'):
            if updates.get('product_type') == ProductTypes.DIRECT.value:
                names = get_resource_service('subscribers').get_subscriber_names({
                    'api_products': original.get(config.ID_FIELD)})
                if names:
                    raise SuperdeskApiError.badRequestError(
                        message=_("Product is used for API publishing for the subscriber(s): {subscribers}").
                        format(subscribers=", ".join(names)))
            elif updates.get('product_type') == ProductTypes.API.value:
                names = get_resource_service('subscribers').get_subscriber_names(
                    {'products': original.get(config.ID_FIELD)})
                if names:
                    raise SuperdeskApiError.badRequestError(
                        message=_("Product is used for direct publishing for the subscriber(s): {subscribers}").
                        format(subscribers=", ".join(names)))

    def get_product_names(self, lookup):
        """Get the product names based on the lookup.
        :param dict lookup: search criteria
        :return list: list of product names
        """
        req = ParsedRequest()
        products = list(get_resource_service('products').get(req=req, lookup=lookup))
        return [product['name'] for product in products]
