
import superdesk

from bson import ObjectId
from copy import copy
from flask import json
from superdesk.tests import TestCase
from content_api.publish import MONGO_PREFIX
from content_api.tokens import generate_subscriber_token
from content_api.app import get_app


class ContentAPITestCase(TestCase):

    def setUp(self):
        self.content_api = superdesk.get_resource_service('content_api')
        self.db = self.app.data.mongo.pymongo(prefix=MONGO_PREFIX).db
        self.app.config['SECRET_KEY'] = 'secret'
        config = copy(self.app.config)
        config['AMAZON_CONTAINER_NAME'] = None  # force gridfs
        config['SERVER_NAME'] = 'localhost:5400'
        config['URL_PREFIX'] = ''
        self.capi = get_app(config)
        self.capi.testing = True

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
        subscribers = [{'_id': ObjectId()}, {'_id': ObjectId()}]

        self.content_api.publish(item, subscribers)
        self.assertEqual(1, self.db.items.find({'subscribers': str(subscribers[0]['_id'])}).count())
        self.assertEqual(0, self.db.items.find({'subscribers': 'foo'}).count())

    def test_content_filtering_by_subscriber(self):
        subscriber = {'_id': 'sub1'}
        headers = self._auth_headers(subscriber)

        self.content_api.publish({'_id': 'foo', 'guid': 'foo', 'type': 'text'}, [subscriber])
        self.content_api.publish({'_id': 'bar', 'guid': 'bar', 'type': 'text'}, [])
        self.content_api.publish({'_id': 'pkg', 'guid': 'pkg', 'type': 'composite'}, [subscriber])
        self.content_api.publish({'_id': 'pkg2', 'guid': 'pkg2', 'type': 'composite'}, [])

        with self.capi.test_client() as c:
            response = c.get('items')
            self.assertEqual(401, response.status_code)
            response = c.get('items', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertEqual(1, len(data['_items']))
            self.assertNotIn('subscribers', data['_items'][0])
            self.assertEqual('http://localhost:5400/items/foo', data['_items'][0]['uri'])
            response = c.get('packages', headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, len(data['_items']))
            self.assertEqual('http://localhost:5400/packages/pkg', data['_items'][0]['uri'])

    def test_content_api_picture(self):
        self.content_api.publish({
            '_id': 'foo', 'guid': 'foo', 'type': 'picture', 'headline': 'foo',
            'renditions': {
                'original': {
                    'media': 'abcd1234',
                    'width': 300,
                    'height': 200,
                    'mimetype': 'image/jpeg',
                    'href': 'foo',
                }
            }
        })

        headers = self._auth_headers({'_id': 'sub'})

        with self.capi.test_client() as c:
            response = c.get('items/foo', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertIn('renditions', data)
            rendition = data['renditions']['original']
            self.assertNotIn('media', rendition)
            self.assertEqual('http://localhost:5400/assets/abcd1234', rendition['href'])

            response = c.get(rendition['href'])
            self.assertEqual(401, response.status_code)

            response = c.get(rendition['href'], headers=headers)
            self.assertEqual(404, response.status_code)

    def _auth_headers(self, sub):
        token = generate_subscriber_token(sub)
        headers = {'Authorization': b'Bearer ' + token}
        return headers
