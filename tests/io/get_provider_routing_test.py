# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from unittest import mock
from unittest.mock import MagicMock, patch

from superdesk.tests import TestCase


class FakeSuperdesk():

    def __init__(self):
        self.services = {}  # can be accessed and overriden by test methods

    def get_resource_service(self, service_name):
        return self.services.get(service_name)


fake_superdesk = FakeSuperdesk()


@mock.patch('superdesk.io.commands.update_ingest.superdesk', fake_superdesk)
class GetProviderRoutingSchemeTestCase(TestCase):
    """Tests for the get_provider_routing_scheme() function."""

    def setUp(self):
        try:
            from superdesk.io.commands.update_ingest import (
                get_provider_routing_scheme)
        except ImportError:
            self.fail("Could not import function under test " +
                      "(get_provider_routing_scheme).")
        else:
            self.funcToTest = get_provider_routing_scheme

        fake_superdesk.services = {
            'routing_schemes': MagicMock(name='routing_schemes'),
            'content_filters': MagicMock(name='content_filters')
        }

    def test_returns_none_if_no_provider_scheme_defined(self):
        fake_provider = {'routing_scheme': None}
        result = self.funcToTest(fake_provider)
        self.assertIsNone(result)

    def test_returns_scheme_config_from_db_if_scheme_defined(self):
        fake_scheme = {
            '_id': 'abc123',
            'rules': []
        }
        schemes_service = fake_superdesk.services['routing_schemes']
        schemes_service.find_one.return_value = fake_scheme

        fake_provider = {'routing_scheme': 'abc123'}
        result = self.funcToTest(fake_provider)

        # check that correct scheme has been fetched and returned
        self.assertTrue(schemes_service.find_one.called)
        args, kwargs = schemes_service.find_one.call_args
        self.assertEqual(kwargs.get('_id'), 'abc123')
        self.assertEqual(result, fake_scheme)

    def test_includes_content_filters_in_returned_scheme(self):
        fake_scheme = {
            '_id': 'abc123',
            'rules': [
                {'filter': 'filter_id_4'},
                {'filter': 'filter_id_8'},
            ]
        }
        schemes_service = fake_superdesk.services['routing_schemes']
        schemes_service.find_one.return_value = fake_scheme

        filters_service = fake_superdesk.services['content_filters']
        filters_service.find_one.side_effect = [
            {'_id': 'filter_id_4'},
            {'_id': 'filter_id_8'},
        ]

        fake_provider = {'routing_scheme': 'abc123'}
        result = self.funcToTest(fake_provider)

        scheme_rules = result.get('rules', [])
        self.assertEqual(len(scheme_rules), 2)
        self.assertEqual(scheme_rules[0].get('filter'), {'_id': 'filter_id_4'})
        self.assertEqual(scheme_rules[1].get('filter'), {'_id': 'filter_id_8'})
