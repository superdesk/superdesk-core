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
import json
from copy import copy
from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock

from bson.objectid import ObjectId
from eve.utils import config, ParsedRequest
from eve.versioning import versioned_id_field

from apps.archive.archive import SOURCE as ARCHIVE
from apps.packages.package_service import PackageService
from apps.publish.content.common import BasePublishService
from apps.publish.content.publish import ArchivePublishService
from apps.publish.enqueue import enqueue_published, get_enqueue_service
from apps.publish.published_item import LAST_PUBLISHED_VERSION
from apps.prepopulate.app_populate import AppPopulateCommand
from superdesk import get_resource_service, get_backend
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE
from superdesk.metadata.packages import RESIDREF
from superdesk.publish import init_app, publish_queue
from superdesk.publish.subscribers import SUBSCRIBER_TYPES
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from apps.archive.common import ITEM_OPERATION
from celery.exceptions import SoftTimeLimitExceeded

ARCHIVE_PUBLISH = 'archive_publish'
ARCHIVE_CORRECT = 'archive_correct'
ARCHIVE_KILL = 'archive_kill'

PUBLISH_QUEUE = 'publish_queue'
PUBLISHED = 'published'


@mock.patch('superdesk.publish.subscribers.SubscribersService.generate_sequence_number', lambda self, subscriber: 1)
class ArchivePublishTestCase(TestCase):
    def init_data(self):
        self.users = [{'_id': '1', 'username': 'admin'}]
        self.desks = [{'_id': ObjectId('123456789ABCDEF123456789'), 'name': 'desk1'}]
        self.products = [{"_id": "1", "name": "prod1", "geo_restrictions": "NSW", "email": "test@test.com"},
                         {"_id": "2", "name": "prod2", "codes": "abc,def,"},
                         {"_id": "3", "name": "prod3", "codes": "xyz"}]
        self.subscribers = [{"_id": "1", "name": "sub1", "is_active": True,
                             "subscriber_type": SUBSCRIBER_TYPES.WIRE,
                             "media_type": "media",
                             "sequence_num_settings": {"max": 10, "min": 1},
                             "email": "test@test.com",
                             "products": ["1"],
                             "destinations": [{"name": "dest1", "format": "nitf",
                                               "delivery_type": "ftp",
                                               "config": {"address": "127.0.0.1", "username": "test"}
                                               }]
                             },
                            {"_id": "2", "name": "sub2", "is_active": True,
                             "subscriber_type": SUBSCRIBER_TYPES.WIRE,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "email": "test@test.com",
                             "products": ["1"],
                             "destinations": [{"name": "dest2", "format": "nitf", "delivery_type": "filecopy",
                                               "config": {"address": "/share/copy"}
                                               },
                                              {"name": "dest3", "format": "nitf", "delivery_type": "Email",
                                               "config": {"recipients": "test@sourcefabric.org"}
                                               }]
                             },
                            {"_id": "3", "name": "sub3", "is_active": True,
                             "subscriber_type": SUBSCRIBER_TYPES.DIGITAL,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "email": "test@test.com",
                             "products": ["1"],
                             "destinations": [{"name": "dest1", "format": "nitf",
                                               "delivery_type": "ftp",
                                               "config": {"address": "127.0.0.1", "username": "test"}
                                               }]
                             },
                            {"_id": "4", "name": "sub4", "is_active": True,
                             "subscriber_type": SUBSCRIBER_TYPES.WIRE,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "products": ["1"],
                             "destinations": [{"name": "dest1", "format": "nitf",
                                               "delivery_type": "ftp",
                                               "config": {"address": "127.0.0.1", "username": "test"}
                                               }]
                             },
                            {"_id": "5", "name": "sub5", "is_active": True,
                             "subscriber_type": SUBSCRIBER_TYPES.ALL,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "email": "test@test.com",
                             "codes": "xyz,  klm",
                             "products": ["1", "2"],
                             "destinations": [{"name": "dest1", "format": "ninjs",
                                               "delivery_type": "ftp",
                                               "config": {"address": "127.0.0.1", "username": "test"}
                                               }]
                             }]

        self.articles = [{'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                          '_id': '1',
                          ITEM_TYPE: CONTENT_TYPE.TEXT,
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Test body',
                          'anpa_category': [{'qcode': 'A', 'name': 'Sport'}],
                          'urgency': 4,
                          'headline': 'Two students missing',
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'ednote': 'Andrew Marwood contributed to this article',
                          'dateline': {'located': {'city': 'Sydney'}},
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_STATE: CONTENT_STATE.PUBLISHED,
                          'expiry': utcnow() + timedelta(minutes=20),
                          'slugline': 'story slugline',
                          'unique_name': '#1',
                          'operation': 'publish'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a974-xy4532fe33f9',
                          '_id': '2',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Test body of the second article',
                          'slugline': 'story slugline',
                          'urgency': 4,
                          'anpa_category': [{'qcode': 'A', 'name': 'Sport'}],
                          'headline': 'Another two students missing',
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'ednote': 'Andrew Marwood contributed to this article',
                          'dateline': {'located': {'city': 'Sydney'}},
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'expiry': utcnow() + timedelta(minutes=20),
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_STATE: CONTENT_STATE.PROGRESS,
                          'publish_schedule': "2016-05-30T10:00:00+0000",
                          ITEM_TYPE: CONTENT_TYPE.TEXT,
                          'unique_name': '#2',
                          'operation': 'publish'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fa',
                          '_id': '3',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Test body',
                          'slugline': 'story slugline',
                          'urgency': 4,
                          'anpa_category': [{'qcode': 'A', 'name': 'Sport'}],
                          'headline': 'Two students missing killed',
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'ednote': 'Andrew Marwood contributed to this article killed',
                          'dateline': {'located': {'city': 'Sydney'}},
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_STATE: CONTENT_STATE.KILLED,
                          'expiry': utcnow() + timedelta(minutes=20),
                          ITEM_TYPE: CONTENT_TYPE.TEXT,
                          'unique_name': '#3'},
                         {'guid': '8',
                          '_id': '8',
                          'last_version': 3,
                          config.VERSION: 4,
                          'target_regions': [{'qcode': 'NSW', 'name': 'New South Wales', 'allow': True}],
                          'body_html': 'Take-1 body',
                          'urgency': 4,
                          'headline': 'Take-1 headline',
                          'abstract': 'Abstract for take-1',
                          'anpa_category': [{'qcode': 'A', 'name': 'Sport'}],
                          'pubstatus': 'done',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'dateline': {'located': {'city': 'Sydney'}},
                          'slugline': 'taking takes',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_STATE: CONTENT_STATE.PROGRESS,
                          'expiry': utcnow() + timedelta(minutes=20),
                          ITEM_TYPE: CONTENT_TYPE.TEXT,
                          'unique_name': '#8'},
                         {'_id': '9',
                          'urgency': 3,
                          'headline': 'creator',
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_STATE: CONTENT_STATE.FETCHED},
                         {'guid': 'tag:localhost:2015:69b961ab-a7b402fed4fb',
                          '_id': 'test_item_9',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Student Crime. Police Missing.',
                          'urgency': 4,
                          'headline': 'Police Missing',
                          'abstract': 'Police Missing',
                          'anpa_category': [{'qcode': 'A', 'name': 'Australian General News'}],
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'dateline': {'located': {'city': 'Sydney'}},
                          'slugline': 'Police Missing',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_STATE: CONTENT_STATE.PROGRESS,
                          ITEM_TYPE: CONTENT_TYPE.TEXT,
                          'unique_name': '#9'},
                         {'guid': 'tag:localhost:10:10:10:2015:69b961ab-2816-4b8a-a584-a7b402fed4fc',
                          '_id': '100',
                          config.VERSION: 3,
                          'task': {'user': '1', 'desk': '123456789ABCDEF123456789'},
                          ITEM_TYPE: CONTENT_TYPE.COMPOSITE,
                          'groups': [{'id': 'root', 'refs': [{'idRef': 'main'}], 'role': 'grpRole:NEP'},
                                     {'id': 'main',
                                      'refs': [{'location': ARCHIVE, ITEM_TYPE: CONTENT_TYPE.COMPOSITE, RESIDREF: '6'}],
                                      'role': 'grpRole:main'}],
                          'firstcreated': utcnow(),
                          'expiry': utcnow() + timedelta(minutes=20),
                          'unique_name': '#100',
                          ITEM_STATE: CONTENT_STATE.PROGRESS}]

    def setUp(self):
        self.init_data()

        self.app.data.insert('users', self.users)
        self.app.data.insert('desks', self.desks)
        self.app.data.insert('products', self.products)
        self.app.data.insert('subscribers', self.subscribers)
        self.app.data.insert(ARCHIVE, self.articles)

        self.filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), "validators.json")
        self.json_data = [
            {"_id": "kill_text", "act": "kill", "type": "text", "schema": {"headline": {"type": "string"}}},
            {"_id": "publish_text", "act": "publish", "type": "text", "schema": {}},
            {"_id": "correct_text", "act": "correct", "type": "text", "schema": {}},
            {"_id": "publish_composite", "act": "publish", "type": "composite", "schema": {}},
        ]
        self.article_versions = self._init_article_versions()

        with open(self.filename, "w+") as file:
            json.dump(self.json_data, file)
        init_app(self.app)
        AppPopulateCommand().run(self.filename)

        self.app.media.url_for_media = MagicMock(return_value='url_for_media')
        self._put = self.app.media.put
        self.app.media.put = MagicMock(return_value='media_id')

    def tearDown(self):
        self.app.media.put = self._put
        if self.filename and os.path.exists(self.filename):
            os.remove(self.filename)

    def _init_article_versions(self):
        resource_def = self.app.config['DOMAIN']['archive_versions']
        version_id = versioned_id_field(resource_def)
        return [{'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 version_id: '1',
                 ITEM_TYPE: CONTENT_TYPE.TEXT,
                 config.VERSION: 1,
                 'urgency': 4,
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'dateline': {'located': {'city': 'Sydney'}},
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 ITEM_STATE: CONTENT_STATE.DRAFT,
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 version_id: '1',
                 ITEM_TYPE: CONTENT_TYPE.TEXT,
                 config.VERSION: 2,
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'dateline': {'located': {'city': 'Sydney'}},
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 ITEM_STATE: CONTENT_STATE.SUBMITTED,
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 version_id: '1',
                 ITEM_TYPE: CONTENT_TYPE.TEXT,
                 config.VERSION: 3,
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article',
                 'dateline': {'located': {'city': 'Sydney'}},
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 ITEM_STATE: CONTENT_STATE.PROGRESS,
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 version_id: '1',
                 ITEM_TYPE: CONTENT_TYPE.TEXT,
                 config.VERSION: 4,
                 'body_html': 'Test body',
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article',
                 'dateline': {'located': {'city': 'Sydney'}},
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 ITEM_STATE: CONTENT_STATE.PROGRESS,
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'}]

    def _is_publish_queue_empty(self):
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(0, queue_items.count())

    def _add_content_filters(self, product, is_global=False):
        product['content_filter'] = {'filter_id': 1, 'filter_type': 'blocking'}
        self.app.data.insert('filter_conditions',
                             [{'_id': 1,
                               'field': 'headline',
                               'operator': 'like',
                               'value': 'tor',
                               'name': 'test-1'}])
        self.app.data.insert('filter_conditions',
                             [{'_id': 2,
                               'field': 'urgency',
                               'operator': 'in',
                               'value': '2',
                               'name': 'test-2'}])
        self.app.data.insert('filter_conditions',
                             [{'_id': 3,
                               'field': 'headline',
                               'operator': 'endswith',
                               'value': 'tor',
                               'name': 'test-3'}])
        self.app.data.insert('filter_conditions',
                             [{'_id': 4,
                               'field': 'urgency',
                               'operator': 'in',
                               'value': '2,3,4',
                               'name': 'test-4'}])

        get_resource_service('content_filters').post([{'_id': 1, 'name': 'pf-1', 'is_global': is_global,
                                                       'content_filter': [{"expression": {"fc": [4, 3]}},
                                                                          {"expression": {"fc": [1, 2]}}]
                                                       }])

    def test_publish(self):
        doc = self.articles[3].copy()
        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc['_id'], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED})
        published_doc = get_resource_service(ARCHIVE).find_one(req=None, _id=doc['_id'])
        self.assertIsNotNone(published_doc)
        self.assertEqual(published_doc[config.VERSION], doc[config.VERSION] + 1)
        self.assertEqual(published_doc[ITEM_STATE], ArchivePublishService().published_state)

    def test_versions_across_collections_after_publish(self):
        self.app.data.insert('archive_versions', self.article_versions)

        # Publishing an Article
        doc = self.articles[3]
        original = doc.copy()

        published_version_number = original[config.VERSION] + 1
        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc[config.ID_FIELD],
                                                    updates={ITEM_STATE: CONTENT_STATE.PUBLISHED,
                                                             config.VERSION: published_version_number})

        article_in_production = get_resource_service(ARCHIVE).find_one(req=None, _id=original[config.ID_FIELD])
        self.assertIsNotNone(article_in_production)
        self.assertEqual(article_in_production[ITEM_STATE], CONTENT_STATE.PUBLISHED)
        self.assertEqual(article_in_production[config.VERSION], published_version_number)

        enqueue_published()

        lookup = {'item_id': original[config.ID_FIELD], 'item_version': published_version_number}
        queue_items = list(get_resource_service(PUBLISH_QUEUE).get(req=None, lookup=lookup))
        assert len(queue_items) > 0, \
            "Transmission Details are empty for published item %s" % original[config.ID_FIELD]

        lookup = {'item_id': original[config.ID_FIELD], config.VERSION: published_version_number}
        request = ParsedRequest()
        request.args = {'aggregations': 0}
        items_in_published_collection = list(get_resource_service(PUBLISHED).get(req=request, lookup=lookup))
        assert len(items_in_published_collection) > 0, \
            "Item not found in published collection %s" % original[config.ID_FIELD]

    def test_queue_transmission_for_item_scheduled_future(self):
        self._is_publish_queue_empty()

        doc = copy(self.articles[5])
        doc['item_id'] = doc['_id']
        schedule_date = utcnow() + timedelta(hours=2)
        updates = {
            'publish_schedule': schedule_date,
            'schedule_settings': {
                'utc_publish_schedule': schedule_date
            }
        }
        get_resource_service(ARCHIVE).patch(id=doc['_id'], updates=updates)
        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc['_id'], updates=updates)
        enqueue_published()
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(0, queue_items.count())

    def test_queue_transmission_for_item_scheduled_elapsed(self):
        self._is_publish_queue_empty()

        doc = copy(self.articles[5])
        doc['item_id'] = doc['_id']
        schedule_date = utcnow() + timedelta(minutes=10)
        updates = {
            'publish_schedule': schedule_date,
            'schedule_settings': {
                'utc_publish_schedule': schedule_date
            }
        }
        get_resource_service(ARCHIVE).patch(id=doc['_id'], updates=updates)
        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc['_id'], updates=updates)
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(0, queue_items.count())
        schedule_in_past = utcnow() + timedelta(minutes=-10)
        get_resource_service(PUBLISHED).update_published_items(doc['_id'], 'schedule_settings',
                                                               {'utc_publish_schedule': schedule_in_past})
        get_resource_service(PUBLISHED).update_published_items(doc['_id'], 'publish_schedule', schedule_in_past)

        enqueue_published()
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(1, queue_items.count())

    def test_queue_transmission_for_digital_channels(self):
        self._is_publish_queue_empty()

        doc = copy(self.articles[1])
        doc['item_id'] = doc['_id']

        service = get_enqueue_service(doc[ITEM_OPERATION])
        subscribers, subscriber_codes, associations = \
            service.get_subscribers(doc, SUBSCRIBER_TYPES.DIGITAL)
        service.queue_transmission(doc, subscribers, subscriber_codes)

        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(1, queue_items.count())
        expected_subscribers = ['5']
        for item in queue_items:
            self.assertIn(item["subscriber_id"], expected_subscribers, 'item {}'.format(item))

    def test_queue_transmission_for_wire_channels_with_codes(self):
        self._is_publish_queue_empty()

        doc = copy(self.articles[1])
        doc['item_id'] = doc['_id']

        service = get_enqueue_service(doc[ITEM_OPERATION])
        subscribers, subscriber_codes, associations = \
            service.get_subscribers(doc, SUBSCRIBER_TYPES.WIRE)
        service.queue_transmission(doc, subscribers, subscriber_codes)
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)

        self.assertEqual(1, queue_items.count())
        expected_subscribers = ['5']
        for item in queue_items:
            self.assertIn(item['subscriber_id'], expected_subscribers, 'item {}'.format(item))
            if item['subscriber_id'] == '5':
                self.assertEqual(4, len(item['codes']))
                self.assertIn('def', item['codes'])
                self.assertIn('abc', item['codes'])
                self.assertIn('xyz', item['codes'])
                self.assertIn('klm', item['codes'])

    def test_get_subscribers_without_product(self):
        doc = copy(self.articles[1])
        doc['item_id'] = doc['_id']

        subscriber_service = get_resource_service('subscribers')

        for sub in self.subscribers:
            sub.pop('products', None)
            subscriber_service.delete({'_id': sub['_id']})

        subscriber_service.post(self.subscribers)

        service = get_enqueue_service(doc[ITEM_OPERATION])
        subscribers, subscriber_codes, associations = \
            service.get_subscribers(doc, SUBSCRIBER_TYPES.WIRE)

        self.assertEqual(0, len(subscribers))
        self.assertDictEqual({}, subscriber_codes)

    def test_queue_transmission_wrong_article_type_fails(self):
        self._is_publish_queue_empty()

        doc = copy(self.articles[0])
        doc['item_id'] = doc['_id']
        doc[ITEM_TYPE] = CONTENT_TYPE.PICTURE
        service = get_enqueue_service(doc[ITEM_OPERATION])

        subscribers, subscriber_codes, associations = \
            service.get_subscribers(doc, SUBSCRIBER_TYPES.DIGITAL)
        no_formatters, queued = get_enqueue_service('publish').queue_transmission(doc, subscribers, subscriber_codes)
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(1, queue_items.count())
        self.assertEqual(0, len(no_formatters))
        self.assertTrue(queued)

        subscribers, subscriber_codes, associations = \
            service.get_subscribers(doc, SUBSCRIBER_TYPES.WIRE)
        no_formatters, queued = get_enqueue_service('publish').queue_transmission(doc, subscribers)
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(2, queue_items.count())
        self.assertEqual(0, len(no_formatters))
        self.assertTrue(queued)

    def test_delete_from_queue_by_article_id(self):
        self._is_publish_queue_empty()

        doc = copy(self.articles[3])
        doc['item_id'] = doc['_id']

        archive_publish = get_resource_service(ARCHIVE_PUBLISH)
        archive_publish.patch(id=doc['_id'], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED})

        enqueue_published()
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(6, queue_items.count())

        # this will delete queue transmission for the wire article
        publish_queue.PublishQueueService(PUBLISH_QUEUE, get_backend()).delete_by_article_id(doc['_id'])
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(0, queue_items.count())

    def test_conform_target_regions(self):
        doc = {'headline': 'test'}
        product = {'geo_restrictions': 'QLD'}
        self.assertFalse(get_enqueue_service('publish').conforms_product_targets(product, doc))
        doc = {'headline': 'test', 'target_regions': []}
        self.assertFalse(get_enqueue_service('publish').conforms_product_targets(product, doc))
        doc = {'headline': 'test', 'target_regions': [{'qcode': 'VIC', 'name': 'Victoria', 'allow': True}]}
        self.assertFalse(get_enqueue_service('publish').conforms_product_targets(product, doc))
        doc = {'headline': 'test', 'target_regions': [{'qcode': 'VIC', 'name': 'Victoria', 'allow': False}]}
        self.assertTrue(get_enqueue_service('publish').conforms_product_targets(product, doc))
        doc = {'headline': 'test', 'target_regions': [{'qcode': 'QLD', 'name': 'Queensland', 'allow': True}]}
        self.assertTrue(get_enqueue_service('publish').conforms_product_targets(product, doc))
        doc = {'headline': 'test', 'target_regions': [{'qcode': 'QLD', 'name': 'Queensland', 'allow': False}]}
        self.assertFalse(get_enqueue_service('publish').conforms_product_targets(product, doc))

    def test_conform_target_subscribers(self):
        doc = {'headline': 'test'}
        subscriber = {'_id': 1}
        self.assertTupleEqual((True, False),
                              get_enqueue_service('publish').conforms_subscriber_targets(subscriber, doc))
        doc = {'headline': 'test', 'target_subscribers': []}
        self.assertTupleEqual((True, False),
                              get_enqueue_service('publish').conforms_subscriber_targets(subscriber, doc))
        doc = {'headline': 'test', 'target_subscribers': [{'_id': 2}]}
        self.assertTupleEqual((False, False),
                              get_enqueue_service('publish').conforms_subscriber_targets(subscriber, doc))
        doc = {'headline': 'test', 'target_subscribers': [{'_id': 1}]}
        self.assertTupleEqual((True, True),
                              get_enqueue_service('publish').conforms_subscriber_targets(subscriber, doc))
        doc = {'headline': 'test', 'target_subscribers': [{'_id': 2}], 'target_regions': [{'name': 'Victoria'}]}
        self.assertTupleEqual((True, False),
                              get_enqueue_service('publish').conforms_subscriber_targets(subscriber, doc))

    def test_can_publish_article(self):
        product = self.products[0]
        self._add_content_filters(product, is_global=False)

        service = get_enqueue_service('publish')
        can_it = service.conforms_content_filter(product, self.articles[4])
        self.assertFalse(can_it)
        product['content_filter']['filter_type'] = 'permitting'

        can_it = service.conforms_content_filter(product, self.articles[4])
        self.assertTrue(can_it)
        product.pop('content_filter')

    def test_can_publish_article_with_global_filters(self):
        subscriber = self.subscribers[0]
        product = self.products[0]
        self._add_content_filters(product, is_global=True)

        service = get_resource_service('content_filters')
        req = ParsedRequest()
        req.args = {'is_global': True}
        global_filters = list(service.get(req=req, lookup=None))
        enqueue_service = get_enqueue_service('publish')
        enqueue_service.conforms_global_filter(global_filters, self.articles[4])
        can_it = enqueue_service.conforms_subscriber_global_filter(subscriber, global_filters)
        self.assertFalse(can_it)

        subscriber['global_filters'] = {'1': False}
        can_it = enqueue_service.conforms_subscriber_global_filter(subscriber, global_filters)
        self.assertTrue(can_it)

        product.pop('content_filter')

    def test_is_targeted(self):
        doc = {'headline': 'test'}
        self.assertFalse(BasePublishService().is_targeted(doc))
        doc = {'headline': 'test', 'target_regions': []}
        self.assertFalse(BasePublishService().is_targeted(doc))
        doc = {'headline': 'test', 'target_regions': [{'qcode': 'NSW'}]}
        self.assertTrue(BasePublishService().is_targeted(doc))
        doc = {'headline': 'test', 'target_regions': [], 'target_types': []}
        self.assertFalse(BasePublishService().is_targeted(doc))
        doc = {'headline': 'test', 'target_regions': [], 'target_types': [{'qcode': 'digital'}]}
        self.assertTrue(BasePublishService().is_targeted(doc))

    def test_targeted_for_includes_digital_subscribers(self):
        AppPopulateCommand().run(self.filename)
        updates = {'target_regions': [{'qcode': 'NSW', 'name': 'New South Wales', 'allow': True}]}
        doc_id = self.articles[5][config.ID_FIELD]
        get_resource_service(ARCHIVE).patch(id=doc_id, updates=updates)

        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc_id, updates={ITEM_STATE: CONTENT_STATE.PUBLISHED})
        enqueue_published()
        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(6, queue_items.count())
        expected_subscribers = ['1', '2', '3', '4', '5']
        for item in queue_items:
            self.assertIn(item["subscriber_id"], expected_subscribers, 'item {}'.format(item))

    def test_maintain_latest_version_for_published(self):
        def get_publish_items(item_id, last_version):
            query = {'query': {'filtered': {'filter': {'and': [
                    {'term': {'item_id': item_id}}, {'term': {LAST_PUBLISHED_VERSION: last_version}}
            ]}}}}
            request = ParsedRequest()
            request.args = {'source': json.dumps(query), 'aggregations': 0}
            return self.app.data.find(PUBLISHED, req=request, lookup=None)

        AppPopulateCommand().run(self.filename)
        get_resource_service(ARCHIVE).patch(id=self.articles[1][config.ID_FIELD],
                                            updates={'publish_schedule': None})

        doc = get_resource_service(ARCHIVE).find_one(req=None, _id=self.articles[1][config.ID_FIELD])
        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc[config.ID_FIELD],
                                                    updates={ITEM_STATE: CONTENT_STATE.PUBLISHED})

        enqueue_published()

        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(1, queue_items.count())
        request = ParsedRequest()
        request.args = {'aggregations': 0}
        published_items = self.app.data.find(PUBLISHED, request, None)
        self.assertEqual(1, published_items.count())
        published_doc = next((item for item in published_items
                              if item.get('item_id') == doc[config.ID_FIELD]), None)
        self.assertEqual(published_doc[LAST_PUBLISHED_VERSION], True)

        get_resource_service(ARCHIVE_CORRECT).patch(id=doc[config.ID_FIELD],
                                                    updates={ITEM_STATE: CONTENT_STATE.CORRECTED})

        enqueue_published()

        queue_items = self.app.data.find(PUBLISH_QUEUE, None, None)
        self.assertEqual(2, queue_items.count())
        published_items = self.app.data.find(PUBLISHED, request, None)
        self.assertEqual(2, published_items.count())
        last_published = get_publish_items(published_doc['item_id'], True)
        self.assertEqual(1, last_published.count())

    def test_added_removed_in_a_package(self):
        package = {"groups": [{"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                              {"id": "main", "refs": [
                                  {
                                      "renditions": {},
                                      "slugline": "Boat",
                                      "guid": "123",
                                      "headline": "item-1 headline",
                                      "location": "archive",
                                      "type": "text",
                                      "itemClass": "icls:text",
                                      "residRef": "123"
                                  },
                                  {
                                      "renditions": {},
                                      "slugline": "Boat",
                                      "guid": "456",
                                      "headline": "item-2 headline",
                                      "location": "archive",
                                      "type": "text",
                                      "itemClass": "icls:text",
                                      "residRef": "456"
                                  },
                                  {
                                      "renditions": {},
                                      "slugline": "Boat",
                                      "guid": "789",
                                      "headline": "item-3 headline",
                                      "location": "archive",
                                      "type": "text",
                                      "itemClass": "icls:text",
                                      "residRef": "789"
                                  }], "role": "grpRole:main"}],
                   "task": {
                       "user": "#CONTEXT_USER_ID#",
                       "status": "todo",
                       "stage": "#desks.incoming_stage#",
                       "desk": "#desks._id#"},
                   "guid": "compositeitem",
                   "headline": "test package",
                   "state": "submitted",
                   "type": "composite"}

        updates = {"groups": [{"id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"},
                              {"id": "main", "refs": [
                                  {
                                      "renditions": {},
                                      "slugline": "Boat",
                                      "guid": "123",
                                      "headline": "item-1 headline",
                                      "location": "archive",
                                      "type": "text",
                                      "itemClass": "icls:text",
                                      "residRef": "123"
                                  },
                                  {
                                      "renditions": {},
                                      "slugline": "Boat",
                                      "guid": "555",
                                      "headline": "item-2 headline",
                                      "location": "archive",
                                      "type": "text",
                                      "itemClass": "icls:text",
                                      "residRef": "555"
                                  },
                                  {
                                      "renditions": {},
                                      "slugline": "Boat",
                                      "guid": "456",
                                      "headline": "item-2 headline",
                                      "location": "archive",
                                      "type": "text",
                                      "itemClass": "icls:text",
                                      "residRef": "456"
                                  }], "role": "grpRole:main"}],
                   "task": {
                       "user": "#CONTEXT_USER_ID#",
                       "status": "todo",
                       "stage": "#desks.incoming_stage#",
                       "desk": "#desks._id#"},
                   "guid": "compositeitem",
                   "headline": "test package",
                   "state": "submitted",
                   "type": "composite"}

        items = PackageService().get_residrefs(package)
        removed_items, added_items = ArchivePublishService()._get_changed_items(items, updates)
        self.assertEqual(len(removed_items), 1)
        self.assertEqual(len(added_items), 1)

    def test_get_changed_items_no_item_found(self):
        # dummy publishing so that elastic mappings are created.
        doc = self.articles[3].copy()
        get_resource_service(ARCHIVE_PUBLISH).patch(id=doc['_id'], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED})
        removed_items, added_items = get_enqueue_service('publish')._get_changed_items({}, {'item_id': 'test'})
        self.assertEqual(len(removed_items), 0)
        self.assertEqual(len(added_items), 0)

    def test_reload_filters_if_updated(self):
        self.app.data.insert('vocabularies',
                             [{'_id': 'categories', 'items': []},
                              {'_id': 'urgency', 'items': []},
                              {'_id': 'priority', 'items': []},
                              {'_id': 'type', 'items': []},
                              {'_id': 'genre', 'items': []},
                              {'_id': 'place', 'items': []},
                              ])
        product = self.products[0]
        product['content_filter'] = {'filter_id': 1, 'filter_type': 'blocking'}
        self.app.data.insert('filter_conditions',
                             [{'_id': '1',
                               'field': 'headline',
                               'operator': 'like',
                               'value': 'tor',
                               'name': 'test-1',
                               '_updated': utcnow() - timedelta(days=10)}])
        get_enqueue_service('publish')
        get_resource_service('filter_conditions').patch('1', updates={'name': 'test-1 updated'})
        service2 = get_enqueue_service('publish')
        self.assertGreater(service2.filters['latest_filter_conditions'], utcnow() - timedelta(seconds=10))


class TimeoutTest(TestCase):

    published_items = [
        {
            "_id": ObjectId("58006b8d1d41c88eace5179d"),
            "item_id": "1",
            "_created": utcnow(),
            "_updated": utcnow(),
            "queue_state": "pending",
            "state": "published",
            "operation": "publish"
        }]

    def setUp(self):
        with self.app.app_context():
            init_app(self.app)

    @mock.patch('apps.publish.enqueue.get_enqueue_service', side_effect=SoftTimeLimitExceeded())
    def test_soft_timeout_gets_re_queued(self, mock):
        self.app.data.insert('published', self.published_items)
        enqueue_published()
        published = self.app.data.find(PUBLISHED, None, None)
        self.assertTrue(published[0].get('queue_state'), 'pending')
