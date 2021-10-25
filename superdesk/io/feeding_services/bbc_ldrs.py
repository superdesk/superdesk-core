# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import re

from datetime import datetime

from superdesk.errors import IngestApiError, ParserError
from superdesk.io.registry import register_feeding_service
from superdesk.io.feeding_services.http_base_service import HTTPFeedingServiceBase

utcfromtimestamp = datetime.utcfromtimestamp


class BBCLDRSFeedingService(HTTPFeedingServiceBase):
    """
    Feeding Service class for reading BBC's Local Democracy Reporting Service
    """

    # Following the api spec at https://docs.ldrs.org.uk/

    NAME = "bbc_ldrs"
    ERRORS = [ParserError.parseMessageError().get_error_description()]

    label = "BBC Local Democracy Reporter Service"

    fields = [
        {
            "id": "url",
            "type": "text",
            "label": "LDRS URL",
            "placeholder": "LDRS URL",
            "required": True,
            "default": "https://api.ldrs.org.uk/v1/item",
        },
        {
            "id": "api_key",
            "type": "text",
            "label": "API Key",
            "placeholder": "API Key",
            "required": True,
            "default": "",
        },
    ]
    HTTP_AUTH = False

    def __init__(self):
        super().__init__()

    def _test(self, provider):
        config = self.config
        url = config["url"]
        api_key = config["api_key"]

        # limit the data to a single article and filter out all article fields
        # to save bandwidth
        params = {"limit": 1, "fields": "id"}
        headers = {"apikey": api_key}

        self.get_url(url, params=params, headers=headers)

    def _update(self, provider, update):
        json_items = self._fetch_data()
        parsed_items = []

        for item in json_items:
            try:
                parser = self.get_feed_parser(provider, item)
                parsed_items.append(parser.parse(item))
            except Exception as ex:
                raise ParserError.parseMessageError(ex, provider, data=item)

        return parsed_items

    def _fetch_data(self):
        url = self.config["url"]
        api_key = self.config["api_key"]

        last_update = self.provider.get("last_updated", utcfromtimestamp(0)).strftime("%Y-%m-%dT%H:%M:%S")

        # Results are pagified so we'll read this many at a time
        offset_jump = 10

        params = {"start": last_update, "limit": offset_jump}
        headers = {"apikey": api_key}

        items = []

        offset = 0
        while True:
            params["offset"] = offset

            response = self.get_url(url, params=params, headers=headers)
            # The total number of results are given to us in json, get them
            # via a regex to read the field so we don't have to convert the
            # whole thing to json pointlessly
            item_ident = re.search('"total": *[0-9]*', response.text).group()
            results_str = re.search("[0-9]+", item_ident).group()

            if results_str is None:
                raise IngestApiError.apiGeneralError(Exception(response.text), self.provider)

            num_results = int(results_str)

            if num_results > 0:
                items.append(response.text)

            if offset >= num_results:
                return items

            offset += offset_jump

        return items


register_feeding_service(BBCLDRSFeedingService)
