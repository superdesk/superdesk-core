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
URL_ACK = 'https://services.ritzau.dk/ritzaurest/Services.svc/xml/news/QueueAcknowledge'


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
            SuperdeskIngestError.notConfiguredError(Exception('username and password are needed'))

        url_override = config.get('url', '').strip()
        if not url_override.startswith('http'):
            SuperdeskIngestError.notConfiguredError(Exception('if URL is set, it must be a valid http link'))

        if url_override:
            params = {'user': user, 'password': password, 'maksAntal': 50}
        else:
            params = {'user': user, 'password': password, 'maksAntal': 50, 'waitAcknowledge': 'true'}

        try:
            r = requests.get(url_override or URL, params=params)
        except Exception as e:
            raise IngestApiError.apiRequestError(Exception('error while doing the request'))

        try:
            root_elt = etree.fromstring(r.text)
        except Exception as e:
            raise IngestApiError.apiRequestError(Exception('error while parsing the request answer'))

        try:
            if root_elt.xpath('(//error/text())[1]')[0] != '0':
                err_msg = root_elt.xpath('(//errormsg/text())[1]')[0]
                raise IngestApiError.apiRequestError(Exception('error code returned by API: {msg}'.format(msg=err_msg)))
        except IndexError as e:
            raise IngestApiError.apiRequestError(Exception('Invalid XML, <error> element not found'))

        parser = self.get_feed_parser(provider)
        items = []
        for elt in root_elt.xpath('//RBNews'):
            item = parser.parse(elt, provider)
            items.append(item)
            if not url_override:
                try:
                    queue_id = elt.xpath('.//ServiceQueueId/text()')[0]
                except IndexError:
                    raise IngestApiError.apiRequestError(Exception('missing ServiceQueueId element'))
                ack_params = {'user': user, 'password': password, 'servicequeueid': queue_id}
                try:
                    requests.get(URL_ACK, params=ack_params)
                except Exception as e:
                    raise IngestApiError.apiRequestError(Exception('error while doing the request'))

        return [items]


register_feeding_service(RitzauFeedingService.NAME, RitzauFeedingService(), RitzauFeedingService.ERRORS)
