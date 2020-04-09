# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import copy
from datetime import timedelta
from unittest.mock import MagicMock, patch

from apps.archive.archive import SOURCE as ARCHIVE
from apps.archive.common import remove_media_files
from superdesk import get_resource_service
from superdesk.media.crop import CropService
from superdesk.tests import TestCase
from superdesk.utc import get_expiry_date, utcnow


NOW = utcnow()


class RemoveSpikedContentTestCase(TestCase):
    articles = [{'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 '_id': '1',
                 'type': 'text',
                 'last_version': 3,
                 '_current_version': 4,
                 'body_html': 'Test body',
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'state': 'draft',
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#1'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a974-xy4532fe33f9',
                 '_id': '2',
                 'last_version': 3,
                 '_current_version': 4,
                 'body_html': 'Test body of the second article',
                 'urgency': 4,
                 'headline': 'Another two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'expiry': utcnow() + timedelta(minutes=20),
                 'state': 'draft',
                 'type': 'text',
                 'unique_name': '#2'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fa',
                 '_id': '3',
                 '_current_version': 4,
                 'body_html': 'Test body',
                 'urgency': 4,
                 'headline': 'Two students missing killed',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article killed',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'state': 'draft',
                 'expiry': utcnow() + timedelta(minutes=20),
                 'type': 'text',
                 'unique_name': '#3'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fc',
                 '_id': '4',
                 '_current_version': 3,
                 'state': 'draft',
                 'type': 'composite',
                 'groups': [{'id': 'root', 'refs': [{'idRef': 'main'}], 'role': 'grpRole:NEP'},
                            {
                                'id': 'main',
                                'refs': [
                                    {
                                        'location': 'archive',
                                        'guid': '1',
                                        'residRef': '1',
                                        'type': 'text'
                                    },
                                    {
                                        'location': 'archive',
                                        'residRef': '2',
                                        'guid': '2',
                                        'type': 'text'
                                    }
                                ],
                                'role': 'grpRole:main'}],
                 'firstcreated': utcnow(),
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#4'},
                {'guid': 'tag:localhost:2015:69b961ab-4b8a-a584-2816-a7b402fed4fc',
                 '_id': '5',
                 '_current_version': 3,
                 'state': 'draft',
                 'type': 'composite',
                 'groups': [{'id': 'root', 'refs': [{'idRef': 'main'}, {'idRef': 'story'}], 'role': 'grpRole:NEP'},
                            {
                                'id': 'main',
                                'refs': [
                                    {
                                        'location': 'archive',
                                        'guid': '1',
                                        'residRef': '1',
                                        'type': 'text'
                                    }
                                ],
                                'role': 'grpRole:main'},
                            {
                                'id': 'story',
                                'refs': [
                                    {
                                        'location': 'archive',
                                        'guid': '4',
                                        'residRef': '4',
                                        'type': 'composite'
                                    }
                                ],
                                'role': 'grpRole:story'}],
                 'firstcreated': utcnow(),
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#5'}]

    media = {
        'viewImage': {
            'media': '1592730d582080f4e9fcc2fcf43aa357bda0ed19ffe314ee3248624cd4d4bc54',
            'mimetype': 'image/jpeg',
            'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
            'height': 452,
            'width': 640
        },
        'thumbnail': {
            'media': '52250b4f37da50ee663fdbff057a5f064479f8a8bbd24fb8fdc06135d3f807bb',
            'mimetype': 'image/jpeg',
            'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
            'height': 120,
            'width': 169
        },
        'baseImage': {
            'media': '7a608aa8f51432483918027dd06d0ef385b90702bfeba84ac4aec38ed1660b18',
            'mimetype': 'image/jpeg',
            'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
            'height': 990,
            'width': 1400
        },
        'original': {
            'media': 'stub.jpeg',
            'mimetype': 'image/jpeg',
            'href': 'http://192.168.220.209/api/upload/stub.jpeg/raw?_schema=http',
            'height': 2475,
            'width': 3500
        }
    }

    def test_query_getting_expired_content(self):
        now = utcnow()

        self.app.data.insert(ARCHIVE, [
            {'expiry': get_expiry_date(0), 'state': 'spiked'},
            {'expiry': get_expiry_date(10), 'state': 'spiked'},
            {'expiry': get_expiry_date(20), 'state': 'spiked'},
            {'expiry': get_expiry_date(30), 'state': 'spiked'},
            {'expiry': None, 'state': 'spiked'},
            {'unique_id': 97, 'state': 'spiked'},
            {'expiry': now - timedelta(minutes=10), 'state': 'spiked', 'unique_id': 100},
        ])

        expired_items = get_resource_service(ARCHIVE).get_expired_items(now)
        now = utcnow()
        for expired_items in get_resource_service(ARCHIVE).get_expired_items(now):
            self.assertEquals(1, len(expired_items))
            self.assertEquals(100, expired_items[0]['unique_id'])

    def test_remove_media_files_for_picture(self):
        item = {
            '_id': 'testimage',
            'type': 'picture',
            'renditions': self.media
        }

        original = item.copy()
        with patch.object(self.app.media, 'delete') as media_delete:
            CropService().update_media_references(item, original)
            references_service = get_resource_service('media_references')
            refs = references_service.get(req=None, lookup={'item_id': 'testimage'})
            self.assertEqual(refs.count(), 4)
            for ref in refs:
                self.assertEqual(ref.get('published'), False)
            CropService().update_media_references(item, original, True)
            refs = references_service.get(req=None, lookup={'item_id': 'testimage'})
            for ref in refs:
                self.assertEqual(ref.get('published'), True)

            remove_media_files(item)
            self.assertEqual(0, media_delete.call_count)

            item = {
                '_id': 'testimage2',
                'type': 'picture',
                'renditions': self.media
            }

            original = item.copy()
            CropService().update_media_references(item, original)
            references_service = get_resource_service('media_references')
            refs = references_service.get(req=None, lookup={'item_id': 'testimage2'})
            self.assertEqual(refs.count(), 4)
            for ref in refs:
                self.assertEqual(ref.get('published'), False)

            remove_media_files(item)
            self.assertEqual(0, media_delete.call_count)

            item = {
                '_id': 'testimage3',
                'type': 'picture',
                'renditions': {
                    'viewImage': {
                        'media': '123',
                        'mimetype': 'image/jpeg',
                        'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
                        'height': 452,
                        'width': 640
                    },
                    'thumbnail': {
                        'media': '456',
                        'mimetype': 'image/jpeg',
                        'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
                        'height': 120,
                        'width': 169
                    }
                }
            }

            original = item.copy()
            CropService().update_media_references(item, original)
            references_service = get_resource_service('media_references')
            refs = references_service.get(req=None, lookup={'item_id': 'testimage3'})
            self.assertEqual(refs.count(), 2)
            for ref in refs:
                self.assertEqual(ref.get('published'), False)

            remove_media_files(item)
            self.assertEqual(2, media_delete.call_count)
            for key, rendition in item.get('renditions').items():
                media_delete.assert_any_call(rendition['media'])

    def test_remove_media_files_for_picture_associations(self):
        item = {
            '_id': 'testimage',
            'type': 'text',
            'associations': {
                'featuremedia': {
                    '_id': '123',
                    'renditions': self.media
                },
                'featurevideo': {
                    '_id': '456',
                    'renditions': {
                        'viewImage': {
                            'media': 'testing_123',
                            'mimetype': 'image/jpeg',
                            'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
                            'height': 452,
                            'width': 640
                        },
                        'thumbnail': {
                            'media': 'testing_456',
                            'mimetype': 'image/jpeg',
                            'href': 'http://192.168.220.209/api/upload/abc/raw?_schema=http',
                            'height': 120,
                            'width': 169
                        }
                    }
                }
            }
        }

        original = item.copy()
        with patch.object(self.app.media, 'delete') as media_delete:
            CropService().update_media_references(item, original)
            references_service = get_resource_service('media_references')
            refs = references_service.get(req=None, lookup={'item_id': 'testimage'})
            self.assertEqual(refs.count(), 6)
            for ref in refs:
                self.assertEqual(ref.get('published'), False)
            CropService().update_media_references(item, original, True)
            refs = references_service.get(req=None, lookup={'item_id': 'testimage'})
            for ref in refs:
                self.assertEqual(ref.get('published'), True)

            remove_media_files(item)
            self.assertEqual(0, media_delete.call_count)

    def test_remove_media_files_for_attachments(self):
        attachments = self.app.data.insert('attachments', [{'media': 'foo'}])
        item = {
            '_id': 'test',
            'type': 'text',
            'attachments': [
                {'attachment': attachments[0]},
            ]
        }
        with patch.object(self.app.media, 'delete') as media_delete:
            remove_media_files(item)
        media_delete.assert_any_call('foo', 'attachments')

    def test_delete_by_ids(self):
        ids = self.app.data.insert(ARCHIVE, self.articles)
        archive_service = get_resource_service(ARCHIVE)
        archive_service.on_delete = MagicMock()
        archive_service.delete_by_article_ids(ids)
        self.assertTrue(self.app.data.mongo.is_empty(ARCHIVE))
        self.assertTrue(self.app.data.elastic.is_empty(ARCHIVE))
        self.assertEqual(len(self.articles), archive_service.on_delete.call_count)

    def test_remove_renditions_from_all_versions(self):
        renditions = copy.copy(self.media)

        ids = self.app.data.insert(ARCHIVE, [{
            'state': 'spiked',
            'expiry': get_expiry_date(-10),
            'type': 'picture',
            'renditions': {},
        }])

        self.app.data.insert('archive_versions', [{
            '_id_document': ids[0],
            'type': 'picture',
            'renditions': renditions,
        }])

        with patch.object(self.app.media, 'delete') as media_delete:
            get_resource_service('archive').delete_by_article_ids(ids)
            for key, rendition in renditions.items():
                media_delete.assert_any_call(rendition['media'])

    def _get_original(self, _id):
        return self.app.data.find_one(ARCHIVE, None, _id=_id)
