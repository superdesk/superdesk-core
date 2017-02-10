# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import requests
from datetime import timedelta
from unittest.mock import patch, MagicMock

import superdesk
from superdesk.utc import utcnow
from superdesk.io.registry import register_feeding_service
from superdesk.io.feeding_services.http_service import HTTPFeedingService
from superdesk.tests import TestCase
from superdesk.errors import IngestApiError


TEST_FEEDING_SERVICE_NAME = 'test_feeding_service'


def setup_provider(token, hours):
    return {
        '_id': 'foo',
        'name': 'test http',
        'source': 'test http',
        'feeding_service': TEST_FEEDING_SERVICE_NAME,
        'feed_parser': 'newsml2',
        'content_expiry': 2880,
        'tokens': {
            'auth_token': token,
            'created': utcnow() - timedelta(hours=hours),
        }
    }


class TestFeedingService(HTTPFeedingService):
    NAME = TEST_FEEDING_SERVICE_NAME
    ERRORS = []

    def _update(self, provider, update):
        pass


register_feeding_service(TestFeedingService.NAME, TestFeedingService(), TestFeedingService.ERRORS)


class ErrorResponseSession(MagicMock):

    def get(self, *args, **kwargs):
        response = requests.Response()
        response.status_code = 401
        return response


class GetTokenTestCase(TestCase):
    def test_get_null_token(self):
        provider = {}
        self.assertEquals('', TestFeedingService()._get_auth_token(provider))

    def test_get_existing_token(self):
        provider = setup_provider('abc', 10)
        self.assertEquals('abc', TestFeedingService()._get_auth_token(provider))

    def test_get_expired_token(self):
        """Expired is better than none.."""
        provider = setup_provider('abc', 24)
        self.assertEquals('', TestFeedingService()._get_auth_token(provider))

    def test_fetch_token(self):
        # TODO: need some rewriting
        # this test is not working anymore
        # try to fill os.environ['REUTERS_USERNAME']
        provider = setup_provider('abc', 24)
        superdesk.get_resource_service('ingest_providers').post([provider])
        self.assertTrue(provider.get('_id'))
        provider['config'] = {}
        provider['config']['username'] = ''
        provider['config']['password'] = ''
        # provider['config']['username'] = os.environ.get('REUTERS_USERNAME', '')
        # provider['config']['password'] = os.environ.get('REUTERS_PASSWORD', '')
        # Tests shouldn't depends on some external settings
        # this block should be run always or must be removed %)
        if provider['config']['username']:
            token = TestFeedingService()._generate_auth_token(provider, update=True)
            self.assertNotEquals('', token)
            self.assertEquals(token, provider['tokens']['auth_token'])

            dbprovider = superdesk.get_resource_service('ingest_providers').find_one(name='test http', req=None)
            self.assertEquals(token, dbprovider['tokens']['auth_token'])

    def test_generate_auth_token_raise_on_error(self):
        provider = setup_provider('abc', 24)
        provider['config'] = {'auth_url': 'http://example.com'}
        with patch('requests.Session', new=ErrorResponseSession):
            service = TestFeedingService()
            with self.assertRaises(IngestApiError) as cm:
                service._generate_auth_token(provider)
            self.assertEqual(cm.exception.code, 4007)
