
import io
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
            self.assertIn('items/foo', data['_items'][0]['uri'])
            response = c.get('packages', headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, len(data['_items']))
            self.assertIn('packages/pkg', data['_items'][0]['uri'])

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

        headers = self._auth_headers()

        with self.capi.test_client() as c:
            response = c.get('items/foo', headers=headers)
            self.assertEqual(200, response.status_code)
            data = json.loads(response.data)
            self.assertIn('renditions', data)
            rendition = data['renditions']['original']
            self.assertNotIn('media', rendition)
            self.assertIn('assets/abcd1234', rendition['href'])

            response = c.get(rendition['href'])
            self.assertEqual(401, response.status_code)

            response = c.get(rendition['href'], headers=headers)
            self.assertEqual(404, response.status_code)

            with self.app.app_context():
                data = io.BytesIO(b'content')
                media_id = self.app.media.put(data, resource='upload')
                self.assertIsInstance(media_id, ObjectId, media_id)

            url = 'assets/%s' % media_id
            response = c.get(url, headers=headers)
            self.assertEqual(200, response.status_code, url)
            self.assertEqual(b'content', response.data)

    def test_text_with_pic_associations(self):
        self.content_api.publish({
            'guid': 'text',
            'type': 'text',
            'body_html': '''<p>
            <p>hey</p>
            <!-- EMBED START Image {id: \"foo\"} -->
            <figure>
                <img src=\"http://localhost:5000/api/upload/foo/raw?_schema=http\"
                    alt=\"tractor\"
                    srcset=\"//localhost:5000/api/upload/foo/raw?_schema=http 800w\" />
                <figcaption>tractor</figcaption>
            </figure>
            <!-- EMBED END Image {id: \"embedded12554054581\"} -->
            ''',
            'associations': {
                'foo': {
                    'type': 'picture',
                    'renditions': {
                        'original': {
                            'href': 'http://localhost:5000/api/upload/foo/raw?_schema=http',
                            'media': 'bar'
                        }
                    }
                }
            }
        })

        headers = self._auth_headers()

        with self.capi.test_client() as c:
            response = c.get('items/text', headers=headers)
            data = json.loads(response.data)
            self.assertEqual(1, len(data['associations']))
            renditions = data['associations']['foo']['renditions']
            self.assertIn('assets/bar', renditions['original']['href'])
            self.assertNotIn('http://localhost:5000/api/upload/', data['body_html'])

    def _auth_headers(self, sub=None):
        if sub is None:
            sub = {'_id': 'sub1'}
        token = generate_subscriber_token(sub)
        headers = {'Authorization': b'Bearer ' + token}
        return headers
