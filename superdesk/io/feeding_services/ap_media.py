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
import json
from superdesk.io.registry import register_feeding_service, register_feeding_service_parser
from superdesk.io.feeding_services.http_base_service import HTTPFeedingServiceBase
from superdesk.errors import IngestApiError, SuperdeskIngestError
import requests
import superdesk
from superdesk.io.feed_parsers import nitf
from lxml import etree
from superdesk.utc import utcnow
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)


class APMediaFeedingService(HTTPFeedingServiceBase):
    """
    Feeding Service class which can retrieve articles from Associated Press Media API
    """

    NAME = 'ap media api'

    label = 'AP Media API'

    fields = [
        {
            'id': 'api_url', 'type': 'text', 'label': 'AP Media API URL',
            'required': True, 'default_value': 'https://api.ap.org/media/v/content/feed'
        },
        {
            'id': 'products_url', 'type': 'text', 'label': 'AP Media API Products URL',
            'required': True, 'default_value': 'https://api.ap.org/media/v/account/plans'
        },
        {
            'id': 'apikey', 'type': 'text', 'label': 'API Key',
            'placeholder': 'API key for access to the API', 'required': True
        },
        {
            'id': 'productList', 'type': 'text', 'label': 'Product List',
            'placeholder': 'Use coma separated product id''s for multiple products, empty for all ', 'required': False
        },
        {
            'id': 'availableProducts', 'type': 'text', 'label': 'All Available Products',
            'readonly': True
        },
        {
            'id': 'next_link', 'type': 'text', 'label': 'Next Link',
            'readonly': True
        },
        {
            'id': 'recoverytime', 'type': 'text', 'label': 'Number of hours to recover', 'default_value': '',
            'placeholder': 'Specifying a number will restart the feed from that number of hours in the past'
        },
    ]

    HTTP_AUTH = False

    HTTP_TIMEOUT = 40.0

    def config_test(self, provider=None):
        self._get_products(provider)
        original = superdesk.get_resource_service('ingest_providers').find_one(req=None, _id=provider.get('_id'))
        # If there has been a change in the required products then reset the next link
        if original and (original.get('config', {}).get('productList', '') != provider.get('config', {}).get(
                'productList', '') or original.get('config', {}).get('recoverytime', '') !=
                provider.get('config', {}).get('recoverytime', '')):
            provider['config']['next_link'] = None

    def _get_products(self, provider):
        """
        Get the products that are available for the API Key, effectively ensuring that the key is valid and provide an
         indication of the product codes available in the UI.
        :param provider:
        :return:
        """
        api_key = provider.get('config', {}).get('apikey')
        r = requests.get(provider.get('config', {}).get('products_url') + '?apikey={}'.format(api_key),
                         timeout=self.HTTP_TIMEOUT, verify=False, allow_redirects=True)
        r.raise_for_status()
        productList = []
        products = json.loads(r.text)
        for plan in products.get('data', {}).get('plans'):
            for entitlement in plan.get('entitlements'):
                productList.append('{}'.format(entitlement.get('id')))
        provider['config']['availableProducts'] = ','.join(productList)

    def prepare_href(self, href, mimetype=None):
        href = href + '&apikey=' + self.provider.get('config', {}).get('apikey') if '?' in href else \
            href + '?apikey=' + self.provider.get('config', {}).get('apikey')
        return href

    def _update(self, provider, update):
        self.HTTP_URL = provider.get('config', {}).get('api_url', '')
        self.provider = provider

        # Set the apikey parameter we're going to use it on all calls
        params = dict()
        params['apikey'] = provider.get('config', {}).get('apikey')

        # Use the next link if one is available in the config
        if provider.get('config', {}).get('next_link'):
            r = self.get_url(url=provider.get('config', {}).get('next_link'), params=params,
                             verify=False, allow_redirects=True)
            r.raise_for_status()
        else:
            id_list = provider.get('config', {}).get('productList', '').strip()
            recovery_time = provider.get('config', {}).get('recoverytime', '1')
            recovery_time = recovery_time.strip() if recovery_time else ''
            if recovery_time == '':
                recovery_time = '1'
            start = datetime.strftime(utcnow() - timedelta(hours=int(recovery_time)), '%Y-%m-%dT%H:%M:%SZ')
            # If there has been a list of products defined then we format them for the request, if not all
            # allowed products will be returned.
            if id_list:
                # we remove spaces and empty values from id_list to do a clean list
                id_list = ' OR '.join([id_.strip() for id_ in id_list.split(',') if id_.strip()])
                params['q'] = 'productid:(' + id_list + ') AND mindate:>{}'.format(start)
            else:
                params['q'] = 'mindate:>{}'.format(start)
            params['page_size'] = '100'
            params['versions'] = 'all'

            logger.info('AP Media Start/Recovery time: {} params {}'.format(recovery_time, params))
            r = self.get_url(params=params, verify=False, allow_redirects=True)
            r.raise_for_status()
        try:
            response = json.loads(r.text)
        except Exception:
            raise IngestApiError.apiRequestError(Exception('error parsing response'))

        nextLink = response.get('data', {}).get('next_page')
        # Got the same next link as last time so nothing new
        if nextLink == provider.get('config', {}).get('next_link'):
            logger.info('Nothing new from AP Media')
            return []

        parser = self.get_feed_parser(provider)
        parsed_items = []
        for item in response.get('data', {}).get('items', []):
            try:
                # Get the item meta data
                logger.info('Get AP meta data for "{}" uri: {}'.format(item.get('item', {}).get('headline'),
                                                                       item.get('item', {}).get('uri')))
                r = self.api_get(item.get('item', {}).get('uri'), provider)
                complete_item = json.loads(r.text)

                # Get the nitf rendition of the item
                nitf_ref = complete_item.get('data', {}).get('item', {}).get('renditions', {}).get('nitf', {}).get(
                    'href')
                if nitf_ref:
                    logger.info('Get AP nitf : {}'.format(nitf_ref))
                    r = self.api_get(nitf_ref, provider)
                    root_elt = etree.fromstring(r.content)
                    nitf_item = nitf.NITFFeedParser().parse(root_elt)
                    complete_item['nitf'] = nitf_item
                else:
                    if item.get('item', {}).get('type') == 'text':
                        logger.warning('No NITF for story {}'.format(item.get('item', {}).get('uri')))

                associations = complete_item['data']['item'].get('associations')
                if associations:
                    complete_item['associations'] = {}
                    for key, assoc in associations.items():
                        logger.info('Get AP association "%s"', assoc.get("headline"))
                        related_json = self.api_get(assoc['uri'], provider).json()
                        complete_item['associations'][key] = related_json

                parsed_items.append(parser.parse(complete_item, provider))

            # Any exception processing an indivisual item is swallowed
            except Exception as ex:
                logger.exception(ex)

        # Save the link for next time
        upd_provider = provider.get('config')
        upd_provider['next_link'] = nextLink
        upd_provider['recoverytime'] = None
        update['config'] = upd_provider

        return [parsed_items]

    def api_get(self, url, provider):
        resp = self.get_url(url=url, params={'apikey': provider['config']['apikey']},
                            verify=False, allow_redirects=True)
        resp.raise_for_status()
        return resp


register_feeding_service(APMediaFeedingService)
