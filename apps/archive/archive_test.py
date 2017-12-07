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
import unittest
import superdesk

from datetime import timedelta, datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId
from pytz import timezone

from apps.archive.archive import SOURCE as ARCHIVE, update_image_caption, update_associations
from superdesk.metadata.item import CONTENT_STATE
from apps.archive.common import (
    validate_schedule, remove_media_files,
    format_dateline_to_locmmmddsrc, convert_task_attributes_to_objectId,
    is_genre, BROADCAST_GENRE, get_default_source, set_default_source,
    get_utc_schedule, get_dateline_city
)
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.media.crop import CropService
from superdesk.tests import TestCase
from superdesk.utc import get_expiry_date, utcnow
from apps.publish.content import publish
from unittest import mock

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
                 'subject':[{'qcode': '17004000', 'name': 'Statistics'},
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
                 'subject':[{'qcode': '17004000', 'name': 'Statistics'},
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
                 'subject':[{'qcode': '17004000', 'name': 'Statistics'},
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


class ArchiveTestCase(TestCase):
    def test_validate_schedule(self):
        validate_schedule(utcnow() + timedelta(hours=2))

    def test_validate_schedule_at_utc_zero_hours(self):
        validate_schedule((utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))

    def test_validate_schedule_date_with_datetime_as_string_raises_superdeskApiError(self):
        self.assertRaises(SuperdeskApiError, validate_schedule, "2015-04-27T10:53:48+00:00")

    def test_validate_schedule_date_with_datetime_in_past_raises_superdeskApiError(self):
        self.assertRaises(SuperdeskApiError, validate_schedule, utcnow() + timedelta(hours=-2))

    def _get_located_and_current_utc_ts(self):
        current_ts = utcnow()
        located = {"dateline": "city", "city_code": "Sydney", "state": "NSW", "city": "Sydney", "state_code": "NSW",
                   "country_code": "AU", "tz": "Australia/Sydney", "country": "Australia"}

        current_timestamp = datetime.fromtimestamp(current_ts.timestamp(), tz=timezone(located['tz']))
        if current_timestamp.month == 9:
            formatted_date = 'Sept {}'.format(current_timestamp.strftime('%-d'))
        elif 3 <= current_timestamp.month <= 7:
            formatted_date = current_timestamp.strftime('%B %-d')
        else:
            formatted_date = current_timestamp.strftime('%b %-d')

        return located, formatted_date, current_ts

    def test_format_dateline_to_format_when_only_city_is_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, 'SYDNEY, %s %s -' % (formatted_date, get_default_source()))

    def test_format_dateline_to_format_when_only_city_and_state_are_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()

        located['dateline'] = "city,state"
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, 'SYDNEY, NSW, %s %s -' % (formatted_date, get_default_source()))

    def test_format_dateline_to_format_when_only_city_and_country_are_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()

        located['dateline'] = "city,country"
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, 'SYDNEY, AU, %s %s -' % (formatted_date, get_default_source()))

    def test_format_dateline_to_format_when_city_state_and_country_are_present(self):
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()

        located['dateline'] = "city,state,country"
        formatted_dateline = format_dateline_to_locmmmddsrc(located, current_ts)
        self.assertEqual(formatted_dateline, 'SYDNEY, NSW, AU, %s %s -' % (formatted_date, get_default_source()))

    def test_if_task_attributes_converted_to_objectid(self):
        doc = {
            'task': {
                'user': '562435231d41c835d7b5fb55',
                'desk': ObjectId("562435241d41c835d7b5fb5d"),
                'stage': 'test',
                'last_authoring_desk': 3245,
                'last_production_desk': None
            }
        }

        convert_task_attributes_to_objectId(doc)
        self.assertIsInstance(doc['task']['user'], ObjectId)
        self.assertEqual(doc['task']['desk'], ObjectId("562435241d41c835d7b5fb5d"))
        self.assertEqual(doc['task']['stage'], 'test')
        self.assertEqual(doc['task']['last_authoring_desk'], 3245)
        self.assertIsNone(doc['task']['last_production_desk'])

    def test_if_no_source_defined_on_desk(self):
        desk = {'name': 'sports'}
        self.app.data.insert('desks', [desk])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            '_id': '123',
            'task': {
                'desk': desk['_id'],
                'stage': desk['working_stage']
            },
            'dateline': {
                'located': located,
                'date': current_ts
            }
        }

        set_default_source(doc)
        self.assertEqual(doc['source'], get_default_source())
        self.assertEqual(doc['dateline']['source'], get_default_source())
        self.assertEqual(doc['dateline']['text'], 'SYDNEY, %s %s -' % (formatted_date, get_default_source()))

    def test_if_source_defined_on_desk(self):
        source = 'FOO'
        desk = {'name': 'sports', 'source': source}
        self.app.data.insert('desks', [desk])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            '_id': '123',
            'task': {
                'desk': desk['_id'],
                'stage': desk['working_stage']
            },
            'dateline': {
                'located': located,
                'date': current_ts
            }
        }

        set_default_source(doc)
        self.assertEqual(doc['source'], source)
        self.assertEqual(doc['dateline']['source'], source)
        self.assertEqual(doc['dateline']['text'], 'SYDNEY, %s %s -' % (formatted_date, source))

    def test_if_ingest_provider_source_is_preserved(self):
        desk = {'name': 'sports', 'source': 'FOO'}
        self.app.data.insert('desks', [desk])
        ingest_provider = {'_id': 1, 'source': 'ABC'}
        self.app.data.insert('ingest_providers', [ingest_provider])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            '_id': '123',
            'task': {
                'desk': desk['_id'],
                'stage': desk['working_stage']
            },
            'dateline': {
                'located': located,
                'date': current_ts
            },
            'ingest_provider': 1
        }

        set_default_source(doc)
        self.assertEqual(doc['source'], 'ABC')
        self.assertEqual(doc['dateline']['source'], 'ABC')
        self.assertEqual(doc['dateline']['text'], 'SYDNEY, %s %s -' % (formatted_date, 'ABC'))

    def test_if_ingest_provider_source_is_not_preserved_for_default_ingest(self):
        desk = {'name': 'sports', 'source': 'FOO'}
        self.app.data.insert('desks', [desk])
        ingest_provider = {'_id': 1, 'source': 'AAP'}
        self.app.data.insert('ingest_providers', [ingest_provider])
        located, formatted_date, current_ts = self._get_located_and_current_utc_ts()
        doc = {
            '_id': '123',
            'task': {
                'desk': desk['_id'],
                'stage': desk['working_stage']
            },
            'dateline': {
                'located': located,
                'date': current_ts
            },
            'ingest_provider': 1
        }

        set_default_source(doc)
        self.assertEqual(doc['source'], 'FOO')
        self.assertEqual(doc['dateline']['source'], 'FOO')
        self.assertEqual(doc['dateline']['text'], 'SYDNEY, %s %s -' % (formatted_date, 'FOO'))

    def test_if_image_caption_is_updated(self):
        body = """
        "body_html" : "<p>test 33</p>\n<!-- EMBED START Image {id: \"embedded9127149191\"} -->\n
        <figure><img src=\"http://localhost:5000/api/upload/58ff025eb611402decdb82e1/raw?_schema=http\" alt=\"aa\" />
        <figcaption>[--description--]</figcaption></figure>\n
        <!-- EMBED END Image {id: \"embedded9127149191\"} -->\n<p>faffaf</p>
        """
        changed_body = """
        "body_html" : "<p>test 33</p>\n<!-- EMBED START Image {id: \"embedded9127149191\"} -->\n
        <figure><img src=\"http://localhost:5000/api/upload/58ff025eb611402decdb82e1/raw?_schema=http\" alt=\"aa\" />
        <figcaption>new caption</figcaption></figure>\n
        <!-- EMBED END Image {id: \"embedded9127149191\"} -->\n<p>faffaf</p>
        """
        body = update_image_caption(body, 'embedded9127149191', 'new caption')
        self.assertEqual(body, changed_body)

    def test_update_associations(self):
        doc = {
            'editor_state': [{
                'entityMap': {
                    '1': {
                        'mutability': 'MUTABLE',
                        'type': 'MEDIA',
                        'data': {
                            'media': {
                                'guid': 'guid1',
                                'type': 'picture',
                                'alt_text': 'media 1'
                            }
                        }
                    },
                    '0': {
                        'mutability': 'MUTABLE',
                        'type': 'MEDIA',
                        'data': {
                            'media': {
                                'guid': 'guid0',
                                'type': 'picture',
                                'alt_text': 'media 0'
                            }
                        }
                    },
                    '2': {
                        'mutability': 'MUTABLE',
                        'type': 'MEDIA',
                        'data': {
                            'media': {
                                'guid': 'guid2',
                                'type': 'picture',
                                'alt_text': 'media 2'
                            }
                        }
                    }
                }
            }],
            'associations': {
                'editor_1': {'guid': 'guid10', 'type': 'picture10', 'alt_text': 'media 10'},
                'editor_7': {'guid': 'guid7', 'type': 'picture7', 'alt_text': 'media 7'},
                'featuremedia': {'guid': 'guid11', 'type': 'picture11'}
            }
        }

        update_associations(doc)

        self.assertEqual(len(doc['associations']), 5)
        self.assertEqual(doc['associations']['editor_0'], {'guid': 'guid0', 'type': 'picture', 'alt_text': 'media 0'})
        self.assertEqual(doc['associations']['editor_1'], {'guid': 'guid1', 'type': 'picture', 'alt_text': 'media 1'})
        self.assertEqual(doc['associations']['editor_2'], {'guid': 'guid2', 'type': 'picture', 'alt_text': 'media 2'})
        self.assertEqual(doc['associations']['editor_7'], None)
        self.assertEqual(doc['associations']['featuremedia'], {'guid': 'guid11', 'type': 'picture11'})

    def test_get_dateline_city_None(self):
        self.assertEqual(get_dateline_city(None), '')

    def test_get_dateline_city_located_as_none(self):
        self.assertEqual(get_dateline_city({'located': None}), '')

    def test_get_dateline_city_located_as_none_text_as_none(self):
        self.assertEqual(get_dateline_city({'located': None, 'text': None}), '')

    def test_get_dateline_city_from_text(self):
        self.assertEqual(get_dateline_city({'located': None, 'text': 'Sydney, 9 July AAP'}), 'Sydney')

    def test_get_dateline_city_from_located(self):
        self.assertEqual(get_dateline_city({'located': {'city': 'Melbourne'}, 'text': 'Sydney, 9 July AAP'}),
                         'Melbourne')

    def test_get_dateline_city_from_text_no_city(self):
        self.assertEqual(get_dateline_city({'located': {'city': None}, 'text': 'Sydney, 9 July AAP'}),
                         'Sydney')

    def test_get_dateline_city_from_located_with_country(self):
        self.assertEqual(get_dateline_city({'located': {'country': 'Canada'}, 'text': 'Sydney, 9 July AAP'}),
                         'Sydney')

    def test_get_dateline_city_from_text_with_city_state(self):
        self.assertEqual(get_dateline_city({'located': None, 'text': 'City, State, 9 July AAP'}), 'City, State')

    def test_firstpublished(self):
        """Check that "firstpublihed" field is set correctly

        the test create a story, check firstpublished field, then correct it
        and check again that correction is done and firstpublished has not changed
        """
        archive_service = superdesk.get_resource_service('archive')
        correct_service = superdesk.get_resource_service('archive_correct')
        publish_service = superdesk.get_resource_service('archive_publish')
        item = {'_id': 'foo',
                'guid': 'foo',
                'unique_name': 'foo',
                'type': 'text',
                'state': CONTENT_STATE.SUBMITTED,
                '_current_version': 1,
                'rewrite_of': 'bar'}
        archive_service.create([item])
        with mock.patch.object(publish, 'utcnow', lambda: NOW):
            publish_service.patch('foo', {'body_html': 'original'})
        created = publish_service.find_one(None, _id='foo')
        self.assertEqual(NOW, created['firstpublished'])
        correct_service.patch('foo', {'body_html': 'corrected'})
        # we try to update to check that "firstpublished" is not modified
        # note that utcnow MUST NOT be mocked here, else the test would be pointless
        corrected = publish_service.find_one(None, _id='foo')
        self.assertEqual('corrected', corrected['body_html'])
        self.assertEqual(NOW, corrected['firstpublished'])


class ArchiveCommonTestCase(unittest.TestCase):

    def test_broadcast_content(self):
        content = {
            'genre': [{'name': 'Broadcast Script', 'qcode': 'Broadcast Script'}]
        }

        self.assertTrue(is_genre(content, BROADCAST_GENRE))

    def test_broadcast_content_if_genre_is_none(self):
        content = {
            'genre': None
        }

        self.assertFalse(is_genre(content, BROADCAST_GENRE))

    def test_broadcast_content_if_genre_is_empty_list(self):
        content = {
            'genre': []
        }

        self.assertFalse(is_genre(content, BROADCAST_GENRE))

    def test_broadcast_content_if_genre_is_other_than_broadcast(self):
        content = {
            'genre': [{'name': 'Article', 'qcode': 'Article'}]
        }

        self.assertFalse(is_genre(content, BROADCAST_GENRE))
        self.assertTrue(is_genre(content, 'Article'))

    def test_get_utc_schedule(self):
        embargo_date = utcnow() + timedelta(minutes=10)
        content = {
            'embargo': embargo_date
        }
        utc_schedule = get_utc_schedule(content, 'embargo')
        self.assertEqual(utc_schedule, embargo_date)


class ExpiredArchiveContentTestCase(TestCase):

    def setUp(self):
        try:
            from apps.archive.commands import RemoveExpiredContent
        except ImportError:
            self.fail("Could not import class under test (RemoveExpiredContent).")
        else:
            self.class_under_test = RemoveExpiredContent
            self.published_items = [
                {
                    '_id': 'item1', 'item_id': 'item1', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', '_current_version': 3,
                    'moved_to_legal': True
                },
                {
                    '_id': 'item2', 'item_id': 'item2', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', '_current_version': 3,
                    'moved_to_legal': True
                },
                {
                    '_id': 'item3', 'item_id': 'item3', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', '_current_version': 3,
                    'moved_to_legal': False
                },
                {
                    '_id': 'item4', 'item_id': 'item4', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', '_current_version': 3,
                    'moved_to_legal': True
                }
            ]

            self.queue_items = [
                {
                    '_id': 'item1', 'item_id': 'item1', 'headline': 'headline',
                    'item_version': 3, 'moved_to_legal': True
                },
                {
                    '_id': 'item2', 'item_id': 'item2', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', 'item_version': 3,
                    'moved_to_legal': True
                },
                {
                    '_id': 'item3', 'item_id': 'item3', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', 'item_version': 3,
                    'moved_to_legal': False
                },
                {
                    '_id': 'item4', 'item_id': 'item4', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', 'item_version': 3,
                    'moved_to_legal': False
                },
                {
                    '_id': 'item5', 'item_id': 'item4', 'headline': 'headline',
                    'source': 'aap', 'body_html': 'test', 'item_version': 3,
                    'moved_to_legal': True
                }
            ]

            self.app.data.insert('published', self.published_items)
            self.app.data.insert('publish_queue', self.queue_items)

    def test_items_moved_to_legal_success(self):
        test_items = dict()
        test_items['item1'] = self.published_items[0]
        test_items['item2'] = self.published_items[1]
        result = self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertDictEqual(result, {})

    def test_items_moved_to_legal_fail_if_published_item_not_moved(self):
        test_items = dict()
        test_items['item2'] = self.published_items[1]
        test_items['item3'] = self.published_items[2]
        result = self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertIn('item3', result)

    def test_items_moved_to_legal_fail_if_published_queue_item_not_moved(self):
        test_items = dict()
        test_items['item2'] = self.published_items[1]
        test_items['item3'] = self.published_items[3]
        result = self.class_under_test().check_if_items_imported_to_legal_archive(test_items)
        self.assertIn('item3', result)
