# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.publish.publish_service import PublishService
from superdesk.publish import register_transmitter
from superdesk import get_resource_service
import json


class ContentAPIService(PublishService):
    """Content API Publish Service.

    The Content API push service publishes items to the resource service via the content API
    publish method.
    """

    def _transmit(self, queued_item, subscriber):
        """
        @see: PublishService._transmit
        """
        item = get_resource_service('archive').find_one(req=None, _id=queued_item['item_id'])
        get_resource_service('content_api').publish(json.loads(queued_item['formatted_item']), item, [subscriber])


register_transmitter('content_api', ContentAPIService(), [])
