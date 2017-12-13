# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from eve.utils import ParsedRequest
from superdesk import get_resource_service
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from apps.publish.enqueue.enqueue_service import EnqueueService
from apps.publish.content.common import BasePublishService

logger = logging.getLogger(__name__)


class ProductTestResource(Resource):
    endpoint_name = 'product_tests'
    schema = {
        'article_id': {'type': 'string'}
    }
    url = 'products/test'
    resource_methods = ['POST']
    item_methods = []
    resource_title = endpoint_name
    privileges = {'POST': 'products'}


class ProductTestService(BaseService):

    def create(self, docs, **kwargs):
        archive_service = get_resource_service('archive')
        doc = docs[0]
        if not doc.get('article_id'):
            raise SuperdeskApiError.badRequestError('Article id cannot be empty!')

        article_id = doc.get('article_id')
        article = archive_service.find_one(req=None, _id=article_id)

        if not article:
            raise SuperdeskApiError.badRequestError('Article not found!')

        try:
            results = self.test_products(article)
        except Exception as ex:
            logger.exception(ex)
            raise SuperdeskApiError.badRequestError('Error in testing article: {}'.format(str(ex)))

        doc['_items'] = results
        return [article_id]

    def test_products(self, article, lookup=None):
        req = ParsedRequest()
        results = []
        products = list(get_resource_service('products').get(req=req, lookup=lookup))
        for product in products:
            result = {'product_id': product['_id'], 'matched': True, 'name': product.get('name', '')}
            reason = ''
            if not EnqueueService().conforms_product_targets(product, article):
                # Here it fails to match due to geo restriction
                # story has target_region and product has geo restriction
                result['matched'] = False

                if BasePublishService().is_targeted(article, 'target_regions'):
                    reason = 'Story has target_region'

                if product.get('geo_restrictions'):
                    reason = '{} {}'.format(reason, 'Product has target_region')

            if not EnqueueService().conforms_content_filter(product, article):
                # Here it fails to match due to content filter
                content_filter = product.get('content_filter')
                filter = get_resource_service('content_filters').find_one(req=None, _id=content_filter['filter_id'])
                result['matched'] = False
                reason = 'Story does not match the filter: {}'.format(filter.get('name'))

            result['reason'] = reason
            results.append(result)
        return results
