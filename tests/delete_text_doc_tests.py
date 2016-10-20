
import tempfile

from superdesk.tests import TestCase
from superdesk import get_resource_service
from superdesk.commands.delete_text_doc import DeleteDocCommand


class DeleteDocTestCase(TestCase):

    def setUp(self):
        self.guid = 'urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a'

        self.archived_only_data = [{
            "_id": "test1",
            "guid": self.guid,
            "item_id": "urn:newsml:localhost:2016-09-12T12:11:40.160498:7237e59f-c42d-4865-aee5-e364aeb2966a",
            "_current_version": "1",
            "type": "text",
            "abstract": "test",
            "state": "fetched",
            "slugline": "slugline",
            "headline": "headline",
            "flags": {"marked_archived_only": True},
            "subject": [{"qcode": "17004000", "name": "Statistics"}],
            "body_html": "Test Document body",
            'source': 'AAP',
            'anpa_category': [{
                'qcode': 'test',
                'name': 'Fake',
                'subject': None,
                'scheme': None
            }]
        }]

        self.archivedService = get_resource_service('archived')

    def test_non_text_exception(self):
        self.archived_only_data[0]['type'] = 'fake'
        self.archivedService.post(self.archived_only_data)

        with self.assertRaises(Exception):
            DeleteDocCommand().run([self.guid])

    def test_delete_doc(self):
        self.archivedService.post(self.archived_only_data)
        DeleteDocCommand().run([self.guid])

        cursor = self.archivedService.get(req=None, lookup={'guid': self.guid})
        self.assertEqual(0, len(cursor.docs))

    def test_file_contents_delete(self):
        guids = ['123', '234', '456']
        for guid in guids:
            doc = [{
                "_id": guid,
                "guid": guid,
                "item_id": guid,
                "_current_version": "1",
                "type": "text",
                "abstract": "test",
                "state": "fetched",
                "slugline": "slugline",
                "headline": "headline",
                "flags": {"marked_archived_only": True},
                "subject": [{"qcode": "17004000", "name": "Statistics"}],
                "body_html": "Test Document body",
                'source': 'AAP',
                'anpa_category': [{
                    'qcode': 'test',
                    'name': 'Fake',
                    'subject': None,
                    'scheme': None
                }]
            }]
            self.archivedService.post(doc)

        json = '{"guid": "123"}\n{"guid": "234"}\n'
        f = tempfile.NamedTemporaryFile('w')
        f.write(json)
        f.flush()

        DeleteDocCommand().run(file=f.name)

        cursor = self.archivedService.get(req=None, lookup={})
        self.assertEqual(1, len(cursor.docs))
        self.assertEqual('456', cursor.docs[0]['guid'])
