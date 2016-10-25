
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
