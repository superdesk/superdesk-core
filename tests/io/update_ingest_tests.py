# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import unittest

from unittest import mock
from unittest.mock import MagicMock
from superdesk.tests import TestCase
from datetime import datetime, timedelta
from copy import deepcopy

from superdesk.io.commands.update_ingest import is_not_expired, process_iptc_codes, is_new_version


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


class ItemExpiryTestCase(TestCase):

    def test_expiry_no_dateinfo(self):
        self.assertTrue(is_not_expired({}, None))

    def test_expiry_overflow(self):
        item = {'versioncreated': datetime.now()}
        delta = timedelta(minutes=999999999999)
        self.assertTrue(is_not_expired(item, delta))


class IPTCCodesTestCase(TestCase):

    def test_unknown_iptc(self):
        """Test if an unknown IPTC code is not causing a crash"""
        item = {
            "guid": "urn:newsml:localhost:2019-02-07T12:00:00.030513:369c16e0-d6b7-40e1-8838-9c5f6a61626c",
            "subject": [{"name": "system", "qcode": "99009000"}],
        }
        # item should not be modified
        expected = deepcopy(item)

        with self.app.app_context():
            process_iptc_codes(item, {})
        self.assertEqual(item, expected)


class UtilsTestCase(unittest.TestCase):
    def test_is_new_version(self):
        self.assertTrue(is_new_version({'version': 2}, {'version': 1}))
        self.assertTrue(is_new_version({'versiocreated': datetime.now()},
                                       {'versioncreated': datetime.now() - timedelta(days=1)}))
        self.assertTrue(is_new_version({'version': '10'}, {'version': '2'}))

        self.assertFalse(is_new_version({'version': 1}, {'version': 1}))
        self.assertFalse(is_new_version({'version': '123'}, {'version': '123'}))
        self.assertFalse(is_new_version({'versioncreated': datetime.now()},
                                        {'versioncreated': datetime.now()}))

    def test_is_new_version_content(self):
        self.assertTrue(is_new_version({'headline': 'foo'}, {}))
        self.assertTrue(is_new_version({'headline': 'foo'}, {'headline': 'bar'}))
        self.assertTrue(is_new_version(
            {'renditions': {'original': {'href': 'foo'}}},
            {'renditions': {'original': {'href': 'bar'}}},
        ))
        self.assertTrue(is_new_version(
            {'subject': [{'name': 'foo', 'qcode': 'foo'}]},
            {'subject': [{'name': 'bar', 'qcode': 'bar'}]},
        ))

        self.assertFalse(is_new_version({}, {}))
        self.assertFalse(is_new_version({'headline': 'foo'}, {'headline': 'foo', 'source': 'test'}))
        self.assertFalse(is_new_version(
            {'renditions': {'original': {'href': 'foo'}}},
            {'renditions': {'original': {'href': 'foo'}}},
        ))
        self.assertFalse(is_new_version(
            {'subject': [{'name': 'foo', 'qcode': 'foo'}]},
            {'subject': [{'name': 'foo', 'qcode': 'foo'}]},
        ))

    def test_is_new_version_ignores_expiry(self):
        yesterday = datetime.now() - timedelta(days=1)
        self.assertFalse(is_new_version(
            {'headline': 'foo', 'firstcreated': None, 'expiry': datetime.now()},
            {'headline': 'foo', 'firstcreated': yesterday, 'expiry': yesterday},
        ))
