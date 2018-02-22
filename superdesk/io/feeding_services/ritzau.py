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
from superdesk.io.feeding_services import FeedingService
from superdesk.errors import IngestApiError, SuperdeskIngestError
from lxml import etree
import requests

logger = logging.getLogger(__name__)
URL = 'https://services.ritzau.dk/ritzaurest/Services.svc/xml/news/NewsQueue'


class RitzauFeedingService(FeedingService):
    """
    Feeding Service class which can retrieve articles from Ritzau web service
    """

    NAME = 'ritzau'
    ERRORS = [IngestApiError.apiRequestError().get_error_description(),
              SuperdeskIngestError.notConfiguredError().get_error_description()]

    def _update(self, provider, update):
        try:
            config = provider['config']
            user = config['username']
            password = config['password']
        except KeyError as e:
            SuperdeskIngestError.notConfiguredError(e, 'username and password are needed')

        params = {'user': user, 'password': password, 'maksAntal': 50}
        try:
            r = requests.get(URL, params=params)
        except Exception as e:
            raise IngestApiError.apiRequestError(e, 'error while doing the request')

        try:
            root_elt = etree.fromstring(r.text)
        except Exception as e:
            raise IngestApiError.apiRequestError(e, 'error while parsing the request answer')

        parser = self.get_feed_parser(provider)
        items = []
        for elt in root_elt.xpath('//RBNews'):
            item = parser.parse(elt, provider)
            items.append(item)

        return [items]


register_feeding_service(RitzauFeedingService.NAME, RitzauFeedingService(), RitzauFeedingService.ERRORS)
