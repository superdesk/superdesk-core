
import superdesk

from flask import json
from copy import copy
from superdesk.tests import TestCase
from content_api.publish import MONGO_PREFIX
from content_api.tokens import generate_subscriber_token
from content_api.app import get_app


class ContentAPITestCase(TestCase):

    def setUp(self):
        self.content_api = superdesk.get_resource_service('content_api')
        self.db = self.app.data.mongo.pymongo(prefix=MONGO_PREFIX).db
        self.app.config['SECRET_KEY'] = 'secret'

    def test_publish_to_content_api(self):
        item = {'guid': 'foo', 'type': 'text', 'task': {'desk': 'foo'}}
        self.content_api.publish(item)
        self.assertEqual(1, self.db.items.count())
        self.assertNotIn('task', self.db.items.find_one())
        self.assertEqual('foo', self.db.items.find_one()['_id'])

        self.content_api.publish(item)
        self.assertEqual(1, self.db.items.count())

        item['headline'] = 'foo'
        self.content_api.publish(item)
        self.assertEqual('foo', self.db.items.find_one()['headline'])

    def test_publish_with_subscriber_ids(self):
        item = {'guid': 'foo', 'type': 'text'}
        subscribers = [{'_id': 'sub1'}, {'_id': 'sub2'}]

        self.content_api.publish(item, subscribers)
        self.assertEqual(1, self.db.items.find({'subscribers.sub1': 1}).count())
        self.assertEqual(0, self.db.items.find({'subscribers.sub5': 1}).count())

    def test_content_filtering_by_subscriber(self):
        subscriber = {'_id': 'sub1'}
        token = generate_subscriber_token(subscriber)
        headers = {'Authorization': b'Bearer ' + token}

        self.content_api.publish({'_id': 'foo', 'guid': 'foo', 'type': 'text'}, [subscriber])
        self.content_api.publish({'_id': 'bar', 'guid': 'bar', 'type': 'text'}, [])

        capi = get_app(copy(self.app.config))
        capi.testing = True
        with capi.test_client() as c:
            response = c.get('api/items')
            self.assertEqual(401, response.status_code)
            response = c.get('api/items', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(1, len(data['_items']))
            self.assertNotIn('subscribers', data['_items'][0])
