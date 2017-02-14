# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json
import logging
import content_api
from eve.utils import config, ParsedRequest
from flask import current_app as app
from apps.publish.enqueue.enqueue_service import EnqueueService
from apps.publish.enqueue import EnqueuePublishedService, EnqueueCorrectedService, EnqueueKilledService
from superdesk import get_resource_service
from superdesk.metadata.utils import ProductTypes
from superdesk.publish import PublishingMode

logger = logging.getLogger(__name__)


class EnqueueAPIService(EnqueueService):

    publishing_mode = PublishingMode.API

    def publish(self, doc, target_media_type=None):
        """Queue the content for publishing.

        :param dict doc: document to publish
        :param str target_media_type: dictate if the doc being queued is a Takes Package or an Individual Article.
                Valid values are - Wire, Digital. If Digital then the doc being queued is a Takes Package and if Wire
                then the doc being queues is an Individual Article.
        :return bool: if content is queued then True else False
        :raises PublishQueueError.item_not_queued_error:
                If the nothing is queued.
        """
        queued, subscribers = self._publish(doc, target_media_type)

        # publish to content api
        self.publish_content_api(doc, subscribers)

        return queued

    def publish_content_api(self, doc, subscribers):
        """
        Publish item to content api
        :param dict doc: content api item
        :param list subscribers: list of subscribers
        """
        if content_api.is_enabled() and subscribers:
            get_resource_service('content_api').publish(doc, subscribers)

    def can_apply_product(self, product):
        """Check if the given product can be applied to an item based on publishing.
        If Direct Publishing and product type in 'Direct' or 'Both' then True else False.
        If API Publishing and product type in 'API' or 'Both' then True else False.
        :param dict product: Product to be validated
        :return bool: If Direct Publishing and product type
        """
        return product.get('product_type', 'both') in [ProductTypes.API.value, ProductTypes.BOTH.value]

    def get_destinations(self, subscriber):
        """Get the content api destination for the subscriber
        :param dict subscriber:
        :return list: content api destination.
        """
        destination = next((d for d in (subscriber.get('destinations') or [])
                            if d.get('delivery_type') == 'content_api'), None)
        if not destination:
            return [{'name': 'content api', 'delivery_type': 'content_api', 'format': 'ninjs'}]

        return [destination]

    def get_subscribers_for_previously_sent_items(self, lookup):
        """Returns list of subscribers that have previously received the item.

        :param dict lookup: elastic query to filter the publish queue
        :return: list of subscribers and list of product codes per subscriber
        """
        lookup['$and'].append({'destination.delivery_type': 'content_api'})
        return self._get_subscribers_for_previously_sent_items(lookup)

    def resend(self, doc, subscribers):
        """Resend doc to subscribers.
        If there is any product of type API or both assigned to subscriber
        then the subscriber qualifies for resend.

        :param dict doc: doc to resend
        :param list subscribers: list of subscribers
        :return:
        """
        subscriber_codes = self._get_subscriber_codes(subscribers)
        wire_subscribers = list(self.non_digital(subscribers))
        digital_subscribers = list(self.digital(subscribers))
        req = ParsedRequest()
        req.where = json.dumps({'product_type': {'$in': [ProductTypes.API.value, ProductTypes.BOTH.value]}})
        existing_products = {p[config.ID_FIELD]: p for p in
                             list(get_resource_service('products').get(req=req, lookup=None))}
        api_subscribers = []
        wire_subscribers = [s for s in wire_subscribers
                            for p in (s.get('products') or []) if p in existing_products]
        digital_subscribers = [s for s in digital_subscribers
                               for p in (s.get('products') or []) if p in existing_products]
        if len(wire_subscribers) > 0:
            doc['item_id'] = doc[config.ID_FIELD]
            self._resend_to_subscribers(doc, wire_subscribers, subscriber_codes)
            api_subscribers.extend(wire_subscribers)

        if len(digital_subscribers) > 0:
            if not app.config.get('NO_TAKES', False):
                package = self.takes_package_service.get_take_package(doc)
                package['item_id'] = package[config.ID_FIELD]
                self._resend_to_subscribers(package, digital_subscribers, subscriber_codes)
            else:
                self._resend_to_subscribers(doc, digital_subscribers, subscriber_codes)

                api_subscribers.extend(digital_subscribers)

        self.publish_content_api(doc, api_subscribers)


class EnqueuePublishedAPIService(EnqueueAPIService, EnqueuePublishedService):
    pass


class EnqueueCorrectedAPIService(EnqueueAPIService, EnqueueCorrectedService):
    pass


class EnqueueKilledAPIService(EnqueueAPIService, EnqueueKilledService):
    pass
