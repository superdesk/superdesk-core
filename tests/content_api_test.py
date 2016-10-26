
import superdesk

from superdesk.tests import TestCase
from content_api.publish import MONGO_PREFIX


class ContentAPITestCase(TestCase):

    def setUp(self):
        self.content_api = superdesk.get_resource_service('content_api')
        self.db = self.app.data.mongo.pymongo(prefix=MONGO_PREFIX).db

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
