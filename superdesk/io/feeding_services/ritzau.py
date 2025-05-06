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

from superdesk.io.registry import register_feeding_service, register_feeding_service_parser
from superdesk.io.feeding_services.http_base_service import HTTPFeedingServiceBase
from superdesk.errors import IngestApiError, SuperdeskIngestError
from lxml import etree

logger = logging.getLogger(__name__)
URL_ACK = "https://services.ritzau.dk/ritzaurest/Services.svc/xml/news/QueueAcknowledge"


class RitzauFeedingService(HTTPFeedingServiceBase):
    """
    Feeding Service class which can retrieve articles from Ritzau web service
    """

    NAME = "ritzau"

    ERRORS = [
        IngestApiError.apiRequestError().get_error_description(),
        SuperdeskIngestError.notConfiguredError().get_error_description(),
    ]

    label = "Ritzau feed API"

    fields = HTTPFeedingServiceBase.AUTH_FIELDS + [
        {
            "id": "url",
            "type": "text",
            "label": "URL",
            "placeholder": "fill this field only for advanced uses",
            "required": False,
        }
    ]

    HTTP_URL = "https://services.ritzau.dk/ritzaurest/Services.svc/xml/news/NewsQueue"
    # auth is done with params
    HTTP_AUTH = False

    async def _update(self, provider, update):
        config = self.config
        try:
            user, password = self.config["username"], self.config["password"]
        except KeyError:
            raise await SuperdeskIngestError.notConfiguredError(
                Exception("username and password are needed")
            ).send_notifications()

        url_override = config.get("url", "").strip()
        if url_override and not url_override.startswith("http"):
            raise await SuperdeskIngestError.notConfiguredError(
                Exception("if URL is set, it must be a valid http link")
            ).send_notifications()

        if url_override:
            params = {"user": user, "password": password, "maksAntal": 50}
        else:
            params = {"user": user, "password": password, "maksAntal": 50, "waitAcknowledge": "true"}

        r = await self.get_url(url_override, params=params)

        try:
            root_elt = etree.fromstring(r.text)
        except Exception:
            raise await IngestApiError.apiRequestError(
                Exception("error while parsing the request answer")
            ).send_notifications()

        try:
            if root_elt.xpath("(//error/text())[1]")[0] != "0":
                err_msg = root_elt.xpath("(//errormsg/text())[1]")[0]
                raise await IngestApiError.apiRequestError(
                    Exception("error code returned by API: {msg}".format(msg=err_msg))
                ).send_notifications()
        except IndexError:
            raise await IngestApiError.apiRequestError(
                Exception("Invalid XML, <error> element not found")
            ).send_notifications()

        parser = await self.get_feed_parser(provider)
        items = []
        for elt in root_elt.xpath("//RBNews"):
            item = await parser.parse(elt, provider)
            items.append(item)
            if not url_override:
                try:
                    queue_id = elt.xpath(".//ServiceQueueId/text()")[0]
                except IndexError:
                    raise await IngestApiError.apiRequestError(
                        Exception("missing ServiceQueueId element")
                    ).send_notifications()
                ack_params = {"user": user, "password": password, "servicequeueid": queue_id}
                await self.get_url(URL_ACK, params=ack_params)

        return [items]


register_feeding_service(RitzauFeedingService)
register_feeding_service_parser(RitzauFeedingService.NAME, "ritzau")
