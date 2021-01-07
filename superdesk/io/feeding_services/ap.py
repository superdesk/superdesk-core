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

from superdesk.io.registry import register_feeding_service
from superdesk.io.feeding_services.http_base_service import HTTPFeedingServiceBase
from superdesk.errors import IngestApiError, SuperdeskIngestError
from lxml import etree

logger = logging.getLogger(__name__)
NS = {"iptc": "http://iptc.org/std/nar/2006-10-01/"}


class APFeedingService(HTTPFeedingServiceBase):
    """
    Feeding Service class which can retrieve articles from Associated Press web service
    """

    NAME = "ap"

    label = "AP feed API"

    fields = HTTPFeedingServiceBase.AUTH_FIELDS + [
        {
            "id": "idList",
            "type": "text",
            "label": "Id List",
            "placeholder": "use coma separated ids for multiple values",
            "required": False,
        },
        {
            "id": "idListType",
            "type": "choices",
            "label": "Id List Type",
            "choices": (
                ("products", "Products"),
                ("savedsearches", "Saved searches"),
                ("topics", "Topics"),
                ("offerings", "Offerings"),
                ("packages", "Packages"),
            ),
            "default": "products",
            "required": True,
        },
    ]
    HTTP_URL = "https://syndication.ap.org/AP.Distro.Feed/GetFeed.aspx"

    def config_test(self, provider=None):
        super().config_test(provider)

    def _update(self, provider, update):
        try:
            config = provider["config"]
            id_list = config["idList"]
            # before "products" was hardcoded as value for "idListType"
            id_list_type = config.get("idListType", "products")
            if not id_list.strip():
                raise KeyError
        except KeyError:
            raise SuperdeskIngestError.notConfiguredError(Exception("idList is needed"))

        # we check if the provider has been closed since the last update
        try:
            last_closed = provider["last_closed"]["closed_at"]
            last_updated = provider["last_updated"]
        except KeyError:
            pass
        else:
            if last_closed > last_updated and "private" in provider:
                # we reset the private data so only last page of items will be retrieved (cf. SDESK-4372)
                logger.info("reseting private data for provider {source}".format(source=provider.get("source")))
                del provider["private"]

        # we remove spaces and empty values from id_list to do a clean list
        id_list = ",".join([id_.strip() for id_ in id_list.split(",") if id_.strip()])

        params = {
            "idList": id_list,
            "idListType": id_list_type,
            "format": "5",
            "maxItems": "25",
        }
        try:
            min_date_time = provider["private"]["min_date_time"]
            sequence_number = provider["private"]["sequence_number"]
        except KeyError:
            # the provider is new or re-opened, we want last items
            # so we need reverse-chronological order
            chronological = False
        else:
            params["minDateTime"] = min_date_time
            params["sequenceNumber"] = sequence_number
            params["sortOrder"] = "chronological"
            chronological = True

        r = self.get_url(params=params)

        try:
            root_elt = etree.fromstring(r.content)
        except Exception:
            raise IngestApiError.apiRequestError(Exception("error while doing the request"))

        parser = self.get_feed_parser(provider)
        items = parser.parse(root_elt, provider)
        if not chronological:
            items.reverse()

        try:
            min_date_time = root_elt.xpath('//iptc:timestamp[@role="minDateTime"]/text()', namespaces=NS)[0].strip()
            sequence_number = root_elt.xpath("//iptc:transmitId/text()", namespaces=NS)[0].strip()
        except IndexError:
            raise IngestApiError.apiRequestError(Exception("missing minDateTime or transmitId"))
        else:
            update.setdefault("private", {})
            update["private"]["min_date_time"] = min_date_time
            update["private"]["sequence_number"] = sequence_number

        return [items]


register_feeding_service(APFeedingService)
