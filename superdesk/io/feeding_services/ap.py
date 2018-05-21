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
URL = 'https://syndication.ap.org/AP.Distro.Feed/GetFeed.aspx'
NS = {'iptc': 'http://iptc.org/std/nar/2006-10-01/'}


class APFeedingService(FeedingService):
    """
    Feeding Service class which can retrieve articles from Associated Press web service
    """

    NAME = 'ap'
    ERRORS = [IngestApiError.apiRequestError().get_error_description(),
              SuperdeskIngestError.notConfiguredError().get_error_description()]

    def _update(self, provider, update):
        try:
            config = provider['config']
            user = config['username']
            password = config['password']
            id_list = config['idList']
            if not user.strip() or not password.strip() or not id_list.strip():
                raise KeyError
        except KeyError:
            raise SuperdeskIngestError.notConfiguredError(Exception('username, password and idList are needed'))

        # we remove spaces and empty values from id_list to do a clean list
        id_list = ','.join([id_.strip() for id_ in id_list.split(',') if id_.strip()])

        params = {'idList': id_list,
                  'idListType': 'products',
                  'format': '5',
                  'maxItems': '25',
                  'sortOrder': 'chronological'}
        try:
            min_date_time = provider['private']['min_date_time']
            sequence_number = provider['private']['sequence_number']
        except KeyError:
            pass
        else:
            params['minDateTime'] = min_date_time
            params['sequenceNumber'] = sequence_number

        try:
            r = requests.get(URL, auth=(user, password), params=params)
        except Exception:
            raise IngestApiError.apiRequestError(Exception('error while doing the request'))

        try:
            root_elt = etree.fromstring(r.content)
        except Exception:
            raise IngestApiError.apiRequestError(Exception('error while doing the request'))

        parser = self.get_feed_parser(provider)
        items = parser.parse(root_elt, provider)

        try:
            min_date_time = root_elt.xpath('//iptc:timestamp[@role="minDateTime"]/text()', namespaces=NS)[0].strip()
            sequence_number = root_elt.xpath('//iptc:transmitId/text()', namespaces=NS)[0].strip()
        except IndexError:
            raise IngestApiError.apiRequestError(Exception('missing minDateTime or transmitId'))
        else:
            update.setdefault('private', {})
            update['private']['min_date_time'] = min_date_time
            update['private']['sequence_number'] = sequence_number

        return [items]


register_feeding_service(APFeedingService.NAME, APFeedingService(), APFeedingService.ERRORS)
