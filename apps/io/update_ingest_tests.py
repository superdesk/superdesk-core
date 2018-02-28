# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os

from unittest.mock import patch
from datetime import timedelta, datetime
from nose.tools import assert_raises
from eve.utils import ParsedRequest

import superdesk.io.commands.update_ingest as ingest
from apps.io.tests import setup_providers, teardown_providers
from superdesk import etree, get_resource_service
from superdesk.celery_task_utils import mark_task_as_not_running, is_task_running
from superdesk.errors import SuperdeskApiError, ProviderError
from superdesk.io.registry import register_feeding_service, registered_feeding_services
from superdesk.io.commands.remove_expired_content import get_expired_items, RemoveExpiredContent
from superdesk.io.feeding_services import FeedingService
from superdesk.io.feeding_services.file_service import FileFeedingService
from superdesk.tests import TestCase
from superdesk.utc import utcnow


class TestProviderService(FeedingService):

    def _update(self, provider, update):
        return []


register_feeding_service('test', TestProviderService(), [ProviderError.anpaError(None, None).get_error_description()])


class CeleryTaskRaceTest(TestCase):

    def test_the_second_update_fails_if_already_running(self):
        provider = {'_id': 'abc', 'name': 'test provider', 'update_schedule': {'minutes': 1}}
        removed = mark_task_as_not_running(provider['name'], provider['_id'])
        self.assertFalse(removed)
        failed_to_mark_as_running = is_task_running(provider['name'], provider['_id'], {'minutes': 1})
        self.assertFalse(failed_to_mark_as_running, 'Failed to mark ingest update as running')

        failed_to_mark_as_running = is_task_running(provider['name'], provider['_id'], {'minutes': 1})
        self.assertTrue(failed_to_mark_as_running, 'Ingest update marked as running, possible race condition')

        removed = mark_task_as_not_running(provider['name'], provider['_id'])
        self.assertTrue(removed, 'Failed to mark ingest update as not running.')


reuters_guid = 'tag_reuters.com_2014_newsml_KBN0FL0NM:10'


class UpdateIngestTest(TestCase):

    def setUp(self):
        setup_providers(self)

    def tearDown(self):
        teardown_providers(self)

    def _get_provider(self, provider_name):
        return get_resource_service('ingest_providers').find_one(name=provider_name, req=None)

    def _get_provider_service(self, provider):
        provider_service = registered_feeding_services[provider['feeding_service']]
        return provider_service.__class__()

    def test_ingest_items(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        items.extend(provider_service.fetch_ingest(reuters_guid))
        self.assertEqual(12, len(items))
        self.ingest_items(items, provider, provider_service)

    def test_ingest_item_expiry(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        self.assertIsNone(items[1].get('expiry'))
        items[1]['versioncreated'] = utcnow()
        self.ingest_items([items[1]], provider, provider_service)
        self.assertIsNotNone(items[1].get('expiry'))

    def test_ingest_item_sync_if_missing_from_elastic(self):
        provider, provider_service = self.setup_reuters_provider()
        item = provider_service.fetch_ingest(reuters_guid)[0]
        # insert in mongo
        ids = self.app.data._backend('ingest').insert('ingest', [item])
        # check that item is not in elastic
        elastic_item = self.app.data._search_backend('ingest').find_one('ingest', _id=ids[0], req=None)
        self.assertIsNone(elastic_item)
        # trigger sync by fetch
        old_item = get_resource_service('ingest').find_one(_id=ids[0], req=None)
        self.assertIsNotNone(old_item)
        # check that item is synced in elastic
        elastic_item = self.app.data._search_backend('ingest').find_one('ingest', _id=ids[0], req=None)
        self.assertIsNotNone(elastic_item)

    def test_ingest_provider_closed_raises_exception(self):
        provider = {
            'name': 'aap',
            'is_closed': True,
            'source': 'aap',
            'feeding_service': 'file', 'feed_parser': 'nitf',
            'config': {
                'path': '/'
            }
        }

        with assert_raises(SuperdeskApiError) as error_context:
            aap = self._get_provider_service(provider)
            aap.update(provider, {})
        ex = error_context.exception
        self.assertTrue(ex.status_code == 500)

    def test_ingest_provider_closed_when_critical_error_raised(self):
        provider_name = 'AAP'
        provider = self._get_provider(provider_name)
        self.assertFalse(provider.get('is_closed'))
        provider_service = self._get_provider_service(provider)
        provider_service.provider = provider
        provider_service.close_provider(provider, ProviderError.anpaError())
        provider = self._get_provider(provider_name)
        self.assertTrue(provider.get('is_closed'))

    def test_ingest_provider_calls_close_provider(self):
        def mock_update(provider, update):
            raise ProviderError.anpaError()

        provider_name = 'AAP'
        provider = self._get_provider(provider_name)
        self.assertFalse(provider.get('is_closed'))
        provider_service = self._get_provider_service(provider)
        provider_service.provider = provider
        provider_service._update = mock_update
        with assert_raises(ProviderError):
            provider_service.update(provider, {})
        provider = self._get_provider(provider_name)
        self.assertTrue(provider.get('is_closed'))

    def test_is_scheduled(self):
        self.assertTrue(ingest.is_scheduled({}), 'run after create')
        self.assertFalse(ingest.is_scheduled({'last_updated': utcnow()}), 'wait default time 5m')
        self.assertTrue(ingest.is_scheduled({'last_updated': utcnow() - timedelta(minutes=6)}), 'run after 5m')
        self.assertFalse(ingest.is_scheduled({
            'last_updated': utcnow() - timedelta(minutes=6),
            'update_schedule': {'minutes': 10}
        }), 'or wait if provider has specific schedule')
        self.assertTrue(ingest.is_scheduled({
            'last_updated': utcnow() - timedelta(minutes=11),
            'update_schedule': {'minutes': 10}
        }), 'and run eventually')

    def test_change_last_updated(self):
        ingest_provider = {'name': 'test', 'feeding_service': 'file', 'feed_parser': 'nitf', '_etag': 'test'}
        self.app.data.insert('ingest_providers', [ingest_provider])

        ingest.update_provider(ingest_provider)
        provider = self.app.data.find_one('ingest_providers', req=None, _id=ingest_provider['_id'])
        self.assertGreaterEqual(utcnow(), provider.get('last_updated'))
        self.assertEqual('test', provider.get('_etag'))

    def test_filter_expired_items(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        for item in items[:4]:
            item['expiry'] = utcnow() + timedelta(minutes=11)
        self.assertEqual(4, len(ingest.filter_expired_items(provider, items)))

    def test_filter_expired_items_with_no_expiry(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        self.assertEqual(0, len(ingest.filter_expired_items(provider, items)))

    def test_query_getting_expired_content(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        now = utcnow()
        for i, item in enumerate(items):
            item['ingest_provider'] = provider['_id']
            expiry_time = now - timedelta(hours=11)
            if i > 4:
                expiry_time = now + timedelta(minutes=11)

            item['expiry'] = item['versioncreated'] = expiry_time

        service = get_resource_service('ingest')
        service.post(items)
        expiredItems = get_expired_items(provider, 'ingest')
        self.assertEqual(5, expiredItems.count())

    def test_expiring_with_content(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        now = utcnow()
        for i, item in enumerate(items):
            item['ingest_provider'] = provider['_id']
            expiry_time = now - timedelta(hours=11)
            if i > 4:
                expiry_time = now + timedelta(minutes=11)

            item['expiry'] = item['versioncreated'] = expiry_time

        service = get_resource_service('ingest')
        service.post(items)

        # ingest the items and expire them
        before = service.get(req=None, lookup={})
        self.assertEqual(6, before.count())

        remove = RemoveExpiredContent()
        remove.run(provider.get('type'))

        # only one left in ingest
        after = service.get(req=None, lookup={})
        self.assertEqual(1, after.count())

        req = ParsedRequest()
        self.assertEqual(1, self.app.data.elastic.find('ingest', req, {}).count())
        self.assertEqual(1, self.app.data.mongo.find('ingest', req, {}).count())

    def test_removing_expired_items_from_elastic_only(self):
        now = utcnow()
        self.app.data.elastic.insert('ingest', [
            {'_id': 'foo', 'expiry': now - timedelta(minutes=30)},
            {'_id': 'bar', 'expiry': now + timedelta(minutes=30)},
        ])

        RemoveExpiredContent().run()
        self.assertEqual(1, self.app.data.elastic.find('ingest', ParsedRequest(), {}).count())

    def test_expiring_content_with_files(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        for item in items:
            item['ingest_provider'] = provider['_id']

        now = utcnow()
        items[0]['expiry'] = now - timedelta(hours=11)
        items[1]['expiry'] = now - timedelta(hours=11)
        items[2]['expiry'] = now + timedelta(hours=11)
        items[5]['versioncreated'] = now + timedelta(minutes=11)

        # ingest the items and expire them
        self.ingest_items(items, provider, provider_service)

        # four files in grid fs
        current_files = self.app.media.fs('upload').find()
        self.assertEqual(4, current_files.count())

        remove = RemoveExpiredContent()
        remove.run(provider.get('type'))

        # all gone
        current_files = self.app.media.fs('upload').find()
        self.assertEqual(0, current_files.count())

    def test_apply_rule_set(self):
        item = {'body_html': '@@body@@'}

        provider_name = 'reuters'
        provider = self._get_provider(provider_name)
        self.assertEqual('body', ingest.apply_rule_set(item, provider)['body_html'])

        item = {'body_html': '@@body@@'}
        provider_name = 'AAP'
        provider = self._get_provider(provider_name)
        self.assertEqual('@@body@@', ingest.apply_rule_set(item, provider)['body_html'])

    def test_all_ingested_items_have_sequence(self):
        provider, provider_service = self.setup_reuters_provider()
        guid = 'tag_reuters.com_2014_newsml_KBN0FL0NM:10'
        item = provider_service.fetch_ingest(guid)[0]
        get_resource_service("ingest").set_ingest_provider_sequence(item, provider)
        self.assertIsNotNone(item['ingest_provider_sequence'])

    def test_get_task_ttl(self):
        self.assertEqual(300, ingest.get_task_ttl({}))
        provider = {'update_schedule': {'minutes': 10}}
        self.assertEqual(600, ingest.get_task_ttl(provider))
        provider['update_schedule']['hours'] = 1
        provider['update_schedule']['minutes'] = 1
        self.assertEqual(3660, ingest.get_task_ttl(provider))

    def test_get_task_id(self):
        provider = {'name': 'foo', '_id': 'abc'}
        self.assertEqual('update-ingest-foo-abc', ingest.get_task_id(provider))

    def test_is_idle(self):
        provider = dict(idle_time=dict(hours=1, minutes=0))
        provider['last_item_update'] = utcnow()
        self.assertEqual(ingest.get_is_idle(provider), False)
        provider['idle_time']['hours'] = -1
        self.assertEqual(ingest.get_is_idle(provider), True)
        provider['idle_time'] = dict(hours=0, minutes=0)
        self.assertEqual(ingest.get_is_idle(provider), False)

    def test_files_dont_duplicate_ingest(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)

        for item in items:
            item['ingest_provider'] = provider['_id']
            item['expiry'] = utcnow() + timedelta(hours=11)

        # ingest the items
        self.ingest_items(items, provider, provider_service)

        items = provider_service.fetch_ingest(reuters_guid)
        for item in items:
            item['ingest_provider'] = provider['_id']
            item['expiry'] = utcnow() + timedelta(hours=11)

        # ingest them again
        self.ingest_items(items, provider, provider_service)

        # 12 files in grid fs
        current_files = self.app.media.fs('upload').find()
        self.assertEqual(12, current_files.count())

    def test_anpa_category_to_subject_derived_ingest(self):
        vocab = [{'_id': 'categories', 'items': [{'is_active': True, 'name': 'Domestic Sport', 'qcode': 's',
                                                  "subject": "15000000"}]}]
        self.app.data.insert('vocabularies', vocab)

        provider_name = 'DPA'
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        file_path = os.path.join(provider.get('config', {}).get('path', ''), 'IPTC7901_odd_charset.txt')
        provider_service = self._get_provider_service(provider)
        feeding_parser = provider_service.get_feed_parser(provider)
        items = [feeding_parser.parse(file_path, provider)]

        # ingest the items and check the subject code has been derived
        self.ingest_items(items, provider, provider_service)
        self.assertEqual(items[0]['subject'][0]['qcode'], '15000000')

    def test_anpa_category_to_subject_derived_ingest_ignores_inactive_categories(self):
        vocab = [{'_id': 'categories', 'items': [{'is_active': False, 'name': 'Domestic Sport', 'qcode': 's',
                                                  "subject": "15000000"}]}]
        self.app.data.insert('vocabularies', vocab)

        provider_name = 'DPA'
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        file_path = os.path.join(provider.get('config', {}).get('path', ''), 'IPTC7901_odd_charset.txt')
        provider_service = self._get_provider_service(provider)
        feeding_parser = provider_service.get_feed_parser(provider)
        items = [feeding_parser.parse(file_path, provider)]

        # ingest the items and check the subject code has been derived
        self.ingest_items(items, provider, provider_service)
        self.assertNotIn('subject', items[0])

    def test_subject_to_anpa_category_derived_ingest(self):
        vocab = [{'_id': 'iptc_category_map',
                  'items': [{'name': 'Finance', 'category': 'f', 'qcode': '04000000', 'is_active': True}]},
                 {'_id': 'categories',
                  'items': [{'is_active': True, 'name': 'Australian Weather', 'qcode': 'b', 'subject': '17000000'},
                            {'is_active': True, 'name': 'Finance', 'qcode': 'f'}]},
                 {'_id': 'genre', 'items': [{'qcode': 'feature', 'name': 'feature'}]}]

        self.app.data.insert('vocabularies', vocab)

        provider_name = 'AAP'
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        file_path = os.path.join(provider.get('config', {}).get('path', ''), 'nitf-fishing.xml')
        provider_service = self._get_provider_service(provider)
        feeding_parser = provider_service.get_feed_parser(provider)
        with open(file_path, 'r') as f:
            xml_string = etree.etree.fromstring(f.read())
            items = [feeding_parser.parse(xml_string, provider)]
            for item in items:
                item['ingest_provider'] = provider['_id']
                item['expiry'] = utcnow() + timedelta(hours=11)

            # ingest the items and check the subject code has been derived
            self.ingest_items(items, provider, provider_service)
            self.assertEqual(items[0]['anpa_category'][0]['qcode'], 'f')

    def test_subject_to_anpa_category_derived_ingest_ignores_inactive_map_entries(self):
        vocab = [{'_id': 'iptc_category_map',
                  'items': [{'name': 'Finance', 'category': 'f', 'qcode': '04000000', 'is_active': False}]},
                 {'_id': 'categories',
                  'items': [{'is_active': True, 'name': 'Australian Weather', 'qcode': 'b', 'subject': '17000000'}]},
                 {'_id': 'genre', 'items': [{'qcode': 'feature', 'name': 'feature'}]}]

        self.app.data.insert('vocabularies', vocab)

        provider_name = 'AAP'
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        file_path = os.path.join(provider.get('config', {}).get('path', ''), 'nitf-fishing.xml')
        provider_service = self._get_provider_service(provider)
        feeding_parser = provider_service.get_feed_parser(provider)
        with open(file_path, 'r') as f:
            xml_string = etree.etree.fromstring(f.read())
            items = [feeding_parser.parse(xml_string, provider)]
            for item in items:
                item['ingest_provider'] = provider['_id']
                item['expiry'] = utcnow() + timedelta(hours=11)

            # ingest the items and check the subject code has been derived
            self.ingest_items(items, provider, provider_service)
            self.assertNotIn('anpa_category', items[0])

    def test_ingest_cancellation(self):
        provider, provider_service = self.setup_reuters_provider()
        guid = 'tag_reuters.com_2016_newsml_L1N14N0FF:978556838'
        items = provider_service.fetch_ingest(guid)
        for item in items:
            item['ingest_provider'] = provider['_id']
            item['expiry'] = utcnow() + timedelta(hours=11)
        self.ingest_items(items, provider, provider_service)
        guid = 'tag_reuters.com_2016_newsml_L1N14N0FF:1542761538'
        items = provider_service.fetch_ingest(guid)
        for item in items:
            item['ingest_provider'] = provider['_id']
            item['expiry'] = utcnow() + timedelta(hours=11)
        self.ingest_items(items, provider, provider_service)
        ingest_service = get_resource_service('ingest')
        lookup = {'uri': items[0].get('uri')}
        family_members = ingest_service.get_from_mongo(req=None, lookup=lookup)
        self.assertEqual(family_members.count(), 2)
        for relative in family_members:
            self.assertEqual(relative['pubstatus'], 'canceled')
            self.assertEqual(relative['state'], 'killed')

    def test_ingest_update(self):
        provider, provider_service = self.setup_reuters_provider()
        items = provider_service.fetch_ingest(reuters_guid)
        items[0]['ingest_provider'] = provider['_id']
        items[0]['expiry'] = utcnow() + timedelta(hours=11)

        self.ingest_items(items, provider, provider_service)

        self.assertEqual(items[0]['unique_id'], 1)
        original_id = items[0]['_id']

        items = provider_service.fetch_ingest(reuters_guid)
        items[0]['ingest_provider'] = provider['_id']
        items[0]['expiry'] = utcnow() + timedelta(hours=11)
        # change the headline
        items[0]['headline'] = 'Updated headline'

        # ingest the item again
        self.ingest_items(items, provider, provider_service)

        # see the update to the headline and unique_id survives
        elastic_item = self.app.data._search_backend('ingest').find_one('ingest', _id=original_id, req=None)
        self.assertEqual(elastic_item['headline'], 'Updated headline')
        self.assertEqual(elastic_item['unique_id'], 1)
        self.assertEqual(elastic_item['unique_name'], '#1')

    def test_get_article_ids(self):
        provider_name = 'reuters'
        provider, provider_service = self.setup_reuters_provider()
        ids = provider_service._get_article_ids('channel1', utcnow(), utcnow() + timedelta(minutes=-10))
        self.assertEqual(len(ids), 3)
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        self.assertEqual(provider['tokens']['poll_tokens']['channel1'], 'ExwaY31kfnR2Z2J1cWZ2YnxoYH9kfw==')

    def test_unknown_category_ingested_is_removed(self):
        vocab = [
            {'_id': 'categories',
             'items': [{'is_active': True, 'name': 'Australian Weather', 'qcode': 'b', 'subject': '17000000'},
                       {'is_active': True, 'name': 'Finance', 'qcode': 'f'}]}
        ]

        self.app.data.insert('vocabularies', vocab)

        provider_name = 'AP'
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        file_path = os.path.join(provider.get('config', {}).get('path', ''), 'ap_anpa-3.tst')
        provider_service = self._get_provider_service(provider)
        feeding_parser = provider_service.get_feed_parser(provider)
        items = [feeding_parser.parse(file_path, provider)]

        # ingest the items and check the subject code has been derived
        items[0]['versioncreated'] = utcnow()
        self.ingest_items(items, provider, provider_service)
        self.assertTrue(len(items[0]['anpa_category']) == 0)

    def setup_reuters_provider(self):
        provider_name = 'reuters'
        provider = get_resource_service('ingest_providers').find_one(name=provider_name, req=None)
        provider_service = self._get_provider_service(provider)
        provider_service.provider = provider
        provider_service.URL = provider.get('config', {}).get('url')
        return provider, provider_service

    def test_ingest_with_routing_keeps_elastic_in_sync(self):
        provider, provider_service = self.setup_reuters_provider()

        desk = {'name': 'foo'}
        self.app.data.insert('desks', [desk])
        self.assertIsNotNone(desk['_id'])
        self.assertIsNotNone(desk['incoming_stage'])

        now = datetime.now()

        items = [
            {
                'guid': 'main_text',
                'versioncreated': now,
                'headline': 'Headline of the text item',
            },
            {'guid': 'image_1', 'type': 'picture', 'versioncreated': now},
            {'guid': 'image_2', 'type': 'picture', 'versioncreated': now},
            {
                'type': 'composite',
                'guid': 'package:guid:abcd123',
                'versioncreated': now,
                'headline': 'Headline of the text item',
                'groups': [
                    {
                        'id': 'root',
                        'role': 'grpRole:NEP',
                        'refs': [{'idRef': 'main'}],
                    }, {
                        'id': 'main',
                        'role': 'main',
                        'refs': [
                            {'residRef': 'main_text'},
                            {'residRef': 'image_1'},
                            {'residRef': 'image_2'},
                        ],
                    }
                ]
            }
        ]

        all_week_schedule = {
            "day_of_week": [
                "MON",
                "TUE",
                "WED",
                "THU",
                "FRI",
                "SAT",
                "SUN"
            ],
            "hour_of_day_from": "00:00:00",
            "hour_of_day_to": "23:55:00",
            "time_zone": "Europe/Prague"
        }

        routing_scheme = {
            "name": "autofetch",
            "rules": [
                {
                    "filter": None,
                    "actions": {
                        "exit": False,
                        "publish": [],
                        "fetch": [
                            {
                                "stage": desk['incoming_stage'],
                                "desk": desk['_id']
                            }
                        ]
                    },
                    "schedule": all_week_schedule,
                    "name": "fetch"
                },
                {
                    "filter": None,
                    "actions": {
                        "exit": False,
                        "publish": [],
                        "fetch": []
                    },
                    "schedule": all_week_schedule,
                    "name": "empty"
                },
            ]
        }

        ingest_service = get_resource_service('ingest')
        self.ingest_items(items, provider, provider_service, routing_scheme=routing_scheme)

        self.assertEqual(4, ingest_service.get_from_mongo(None, {}).count())
        self.assertEqual(4, ingest_service.get(None, {}).count())

        for item in items:
            lookup = {'guid': item['guid']}
            mongo_item = ingest_service.get_from_mongo(None, lookup)[0]
            elastic_item = ingest_service.get(None, lookup)[0]
            self.assertEqual(mongo_item['_etag'], elastic_item['_etag'], mongo_item['guid'])

    def test_ingest_associated_item_renditions(self):
        provider = {'feeding_service': 'ninjs', '_id': self.providers['ninjs']}
        provider_service = FileFeedingService()
        item = {
            'guid': 'foo',
            'type': 'text',
            'versioncreated': utcnow(),
            'associations': {
                'featuremedia': {
                    'guid': 'bar',
                    'type': 'picture',
                    'versioncreated': utcnow(),
                    'renditions': {
                        'original': {
                            'href': 'https://farm8.staticflickr.com/7300/9203849352_297ea4207d_z_d.jpg',
                            'mimetype': 'image/jpeg',
                            'width': 640,
                            'height': 426,
                        }
                    }
                }
            }
        }

        # avoid transfer_renditions call which would store the picture locally
        # and it would fetch it using superdesk url which doesn't work in test
        with patch('superdesk.io.commands.update_ingest.transfer_renditions'):
            status, ids = ingest.ingest_item(item, provider, provider_service)

        self.assertTrue(status)
        self.assertEqual(2, len(ids))
        self.assertIn('thumbnail', item['associations']['featuremedia']['renditions'])
