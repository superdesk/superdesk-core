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
from unittest.mock import MagicMock, ANY
from datetime import timedelta
from bson import ObjectId

from superdesk.tests import TestCase
from superdesk.utc import utcnow

from superdesk.errors import PublishHTTPPushServerError, PublishHTTPPushClientError
from apps.publish.enqueue import enqueue_service
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE
from superdesk.publish import publish_queue
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE


class TransmitItemsTestCase(TestCase):
    """Tests for the transmit_items() function."""

    def setUp(self):
        try:
            from superdesk.publish.publish_content import transmit_items
        except ImportError:
            self.fail("Could not import function under test (transmit_items).")
        else:
            self.func_under_test = transmit_items

    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    def test_marks_items_as_retrying_in_case_of_failure(self, *mocks):

        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception('Error patching item')

        item_1 = {
            '_id': 'item_1',
            'destination': {},
            'subscriber_id': '1',
            'item_id': 'test',
            'headline': 'test headline',
            'item_version': 4,
            'state': 'pending'
        }

        orig_item = item_1.copy()  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item
        queue_items = [item_1]
        self.func_under_test(queue_items)
        fake_get_service().system_update.assert_called_with('item_1', {'_updated': ANY, 'retry_attempt': 1,
                                                                       'state': 'retrying',
                                                                       'next_retry_attempt_at': ANY}, orig_item)

    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    def test_marks_items_as_retrying_second_time_incase_of_failure(self, *mocks):

        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception('Error patching item')

        item_1 = {
            '_id': 'item_1',
            'destination': {},
            'subscriber_id': '1',
            'item_id': 'test',
            'headline': 'test headline',
            'item_version': 4,
            'state': 'retrying',
            'retry_attempt': 1,
            'next_retry_attempt_at': utcnow() - timedelta(minutes=10)
        }

        orig_item = item_1.copy()  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item
        queue_items = [item_1]
        self.func_under_test(queue_items)

        fake_get_service().system_update.assert_called_with('item_1', {'_updated': ANY, 'retry_attempt': 2,
                                                                       'state': 'retrying',
                                                                       'next_retry_attempt_at': ANY}, orig_item)

    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    def test_marks_items_failed_to_transmit_after_all_retry_attempts(self, *mocks):

        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception('Error patching item')
        self.app.config['MAX_TRANSMIT_RETRY_ATTEMPT'] = 4

        item_1 = {
            '_id': 'item_1',
            'destination': {},
            'subscriber_id': '1',
            'item_id': 'test',
            'headline': 'test headline',
            'item_version': 4,
            'state': 'retrying',
            'retry_attempt': 4,
            'next_retry_attempt_at': utcnow() - timedelta(minutes=10)
        }

        orig_item = item_1.copy()  # item's original state in DB
        fake_get_service().find_one.return_value = orig_item
        queue_items = [item_1]
        self.func_under_test(queue_items)
        fake_get_service().system_update.assert_called_with('item_1', {'_updated': ANY, 'state': 'failed'}, orig_item)

    @mock.patch('superdesk.publish.publish_content.logger')
    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    def test_logs_error_even_when_marking_failed_items_fails(self, *mocks):
        fake_get_service = mocks[0]
        fake_get_service().patch.side_effect = Exception('Error patching item')
        fake_get_service().system_update.side_effect = Exception('Update error')

        item_1 = {
            '_id': 'item_1',
            'subscriber_id': '1',
            'destination': {},
            'item_id': 'test',
            'headline': 'test headline',
            'item_version': 4,
            'state': 'pending'
        }
        queue_items = [item_1]

        fake_get_service().find_one.return_value = item_1
        self.func_under_test(queue_items)
        fake_logger = mocks[1]
        expected_msg = 'Failed to set the state for failed publish queue item item_1.'
        fake_logger.error.assert_any_call(expected_msg)

    def test_transmit_failure(self):
        subscriber = {
            '_id': ObjectId('56c11bd78b84bb00b0a1905e'),
            'sequence_num_settings': {'max': 9999, 'min': 1},
            '_etag': 'f16b7eaa566f68b8d2561c811ec694bdf819784d',
            'is_active': True,
            'destinations': [{'delivery_type': 'email'}],
            'email': 'test@test.com',
            'subscriber_type': 'digital',
            'name': 'Test',
        }

        self.app.data.insert('subscribers', [subscriber])

        item_1 = {'_id': ObjectId(), 'state': 'pending', 'item_id': 'item_1', 'item_version': 4,
                  'headline': 'pending headline', 'destination': {'delivery_type': 'email'},
                  'subscriber_id': subscriber['_id'], 'formatted_item': 'test'}

        self.app.data.insert('publish_queue', [item_1])
        self.func_under_test([item_1])
        failed_item = self.app.data.find_one('publish_queue', req=None, _id=item_1['_id'])
        self.assertEqual(failed_item['state'], 'retrying')
        self.assertEqual(failed_item['retry_attempt'], 1)
        self.assertEqual(failed_item['next_retry_attempt_at'], ANY)

    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    @mock.patch('superdesk.publish.registered_transmitters')
    def test_no_retry_on_http_push_client_error(self, *mocks):
        self.app.config['MAX_TRANSMIT_RETRY_ATTEMPT'] = 4

        item_1 = {
            '_id': 'item_1',
            'destination': {},
            'subscriber_id': '1',
            'item_id': 'test',
            'headline': 'test headline',
            'item_version': 4,
            'state': 'pending'
        }

        orig_item = item_1.copy()  # item's original state in DB

        fake_get_service = mocks[1]
        fake_get_service().find_one.return_value = orig_item
        queue_items = [item_1]

        fake_transmitter = MagicMock()
        fake_transmitter.transmit.side_effect = PublishHTTPPushClientError.httpPushError(Exception('client 4xx'))

        fake_transmitters_list = mocks[0]
        fake_transmitters_list.__getitem__.return_value = fake_transmitter

        self.func_under_test(queue_items)

        fake_get_service().system_update.assert_called_with('item_1', {'_updated': ANY,
                                                                       'state': 'failed'}, orig_item)

    @mock.patch('superdesk.publish.publish_content.get_resource_service')
    @mock.patch('superdesk.publish.registered_transmitters')
    def test_retry_on_http_push_server_error(self, *mocks):
        self.app.config['MAX_TRANSMIT_RETRY_ATTEMPT'] = 4

        item_1 = {
            '_id': 'item_1',
            'destination': {},
            'subscriber_id': '1',
            'item_id': 'test',
            'headline': 'test headline',
            'item_version': 4,
            'state': 'pending'
        }

        orig_item = item_1.copy()  # item's original state in DB

        fake_get_service = mocks[1]
        fake_get_service().find_one.return_value = orig_item
        queue_items = [item_1]

        fake_transmitter = MagicMock()
        fake_transmitter.transmit.side_effect = PublishHTTPPushServerError.httpPushError(Exception('server 5xx'))

        fake_transmitters_list = mocks[0]
        fake_transmitters_list.__getitem__.return_value = fake_transmitter

        self.func_under_test(queue_items)

        fake_get_service().system_update.assert_called_with('item_1', {'_updated': ANY, 'retry_attempt': 1,
                                                                       'state': 'retrying',
                                                                       'next_retry_attempt_at': ANY}, orig_item)


class QueueItemsTestCase(TestCase):
    """Tests for the transmit_items() function."""

    def setUp(self):
        try:
            from superdesk.publish.publish_content import get_queue_items
        except ImportError:
            self.fail("Could not import function under test (transmit_items).")
        else:
            self.func_under_test = get_queue_items
            self.queue_items = [
                {'_id': ObjectId(), 'state': 'pending', 'item_id': 'item_1', 'item_version': 4,
                 'headline': 'pending headline', 'destination': {}},
                {'_id': ObjectId(), 'state': 'retrying', 'item_id': 'item_2', 'item_version': 4,
                 'headline': 'retrying headline', 'retry_attempt': 2,
                 'next_retry_attempt_at': utcnow() + timedelta(minutes=30)},
                {'_id': ObjectId(), 'state': 'success', 'item_id': 'item_3', 'item_version': 4,
                 'headline': 'success headline', 'retry_attempt': 4,
                 'next_retry_attempt_at': utcnow() + timedelta(minutes=-30)},
                {'_id': ObjectId(), 'state': 'failed', 'item_id': 'item_4', 'item_version': 4,
                 'headline': 'failed headline', 'retry_attempt': 10,
                 'next_retry_attempt_at': utcnow() + timedelta(minutes=-30)},
                {'_id': ObjectId(), 'state': 'canceled', 'item_id': 'item_5', 'item_version': 4,
                 'headline': 'canceled headline', 'retry_attempt': 4,
                 'next_retry_attempt_at': utcnow() + timedelta(minutes=-30)},
                {'_id': ObjectId(), 'state': 'retrying', 'item_id': 'item_6', 'item_version': 4,
                 'headline': 'retrying headline', 'retry_attempt': 2,
                 'next_retry_attempt_at': utcnow() + timedelta(minutes=-30)},
            ]
            self.app.data.insert('publish_queue', self.queue_items)

    def test_get_queue_items(self):
        items = list(self.func_under_test())
        self.assertEqual(len(items), 1)
        for item in items:
            self.assertIn(item['item_id'], ['item_1'])

    def test_get_retry_queue_items(self):
        items = list(self.func_under_test(True))
        self.assertEqual(len(items), 1)
        for item in items:
            self.assertIn(item['item_id'], ['item_6'])

    def test_get_queue_items_with_retrying_items(self):
        item = self.app.data.find_one('publish_queue', req=None, _id=self.queue_items[1]['_id'])
        self.app.data.update('publish_queue', item.get('_id'),
                             {'next_retry_attempt_at': utcnow() - timedelta(minutes=30)},
                             item)
        items = list(self.func_under_test(True))
        self.assertEqual(len(items), 2)
        self.assertListEqual([item_l['item_id'] for item_l in items], ['item_2', 'item_6'])

    @mock.patch.object(enqueue_service, 'ObjectId')
    @mock.patch.object(enqueue_service, 'get_utc_schedule')
    @mock.patch.object(enqueue_service, 'get_resource_service')
    @mock.patch.object(enqueue_service, 'get_formatter')
    def test_enqueue_dict(self, *mocks):
        get_formatter, get_resource_service, _, _ = mocks
        publish_queue = get_resource_service.return_value
        fake_post = publish_queue.post
        service = enqueue_service.EnqueueService()
        fake_formatter = get_formatter.return_value
        doc_dict = {ITEM_TYPE: CONTENT_TYPE.TEXT, PUBLISHED_IN_PACKAGE: False}
        fake_doc = MagicMock()
        fake_doc.__getitem__ = lambda s, k: doc_dict.get(k, MagicMock())
        fake_doc.get = doc_dict.get
        fake_destination = MagicMock()
        fake_subscriber = MagicMock()
        subs_dict = {'destinations': [fake_destination], 'api_enabled': False}
        fake_subscriber.__getitem__ = lambda s, k: subs_dict.get(k, MagicMock())
        fake_subscriber['destinations'] = [fake_destination]
        subscribers = [fake_subscriber]
        fake_formatter.format.return_value = [{'published_seq_num': 42,
                                               'formatted_item': 'test OK'}]
        service.get_destinations = MagicMock(return_value=fake_subscriber['destinations'])
        service.queue_transmission(fake_doc, subscribers)
        self.assertEqual(len(fake_post.call_args_list), 1)
        self.assertEqual(len(fake_post.call_args_list[0][0][0]), 1)
        doc = fake_post.call_args_list[0][0][0][0]
        self.assertEqual(doc['published_seq_num'], 42)
        self.assertEqual(doc['formatted_item'], 'test OK')

        fake_post = publish_queue.post = MagicMock()
        fake_formatter.format.return_value = [{'this_should_not': 'work',
                                               'bad_key': 'value'}]
        service.queue_transmission(fake_doc, subscribers)
        # post should not have been called here,
        # because the dict is lacking the mandatory keys
        self.assertFalse(fake_post.called)

        fake_post = publish_queue.post = MagicMock()
        fake_formatter.format.return_value = [(42, 'test tuple OK')]
        service.queue_transmission(fake_doc, subscribers)
        self.assertEqual(len(fake_post.call_args_list), 1)
        self.assertEqual(len(fake_post.call_args_list[0][0][0]), 1)
        doc = fake_post.call_args_list[0][0][0][0]
        self.assertEqual(doc['published_seq_num'], 42)
        self.assertEqual(doc['formatted_item'], 'test tuple OK')

        fake_post = publish_queue.post = MagicMock()
        fake_formatter.format.return_value = [(1, "2", 3)]
        service.queue_transmission(fake_doc, subscribers)
        # post should not have been called here,
        # because the tuple should be in (published_seq_num, formatted_item) format
        self.assertFalse(fake_post.called)

    @mock.patch.object(publish_queue, 'app')
    def test_delete_encoded_item(self, fake_app):
        fake_storage = fake_app.storage
        fake_storage_delete = fake_storage.delete
        service = publish_queue.PublishQueueService(backend=MagicMock())
        service.get_from_mongo = MagicMock()
        service.get_from_mongo.return_value = [{'_id': "4567", 'encoded_item_id': 'TEST ID'}]
        service.delete({'_id': "4567"})
        fake_storage_delete.call_args == mock.call('TEST ID')
