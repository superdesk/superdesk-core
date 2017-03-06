# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from unittest import mock
from nose.tools import assert_raises
from ..media import get_picture_fixture
from superdesk.tests import TestCase
from superdesk.media.crop import CropService
from superdesk.errors import SuperdeskApiError
from superdesk.vocabularies.command import populate_table_json
from superdesk.media.media_operations import crop_image
from superdesk.media.renditions import _resize_image, get_renditions_spec, can_generate_custom_crop_from_original


class CropTestCase(TestCase):

    crop_sizes = {
        "_id": "crop_sizes",
        "display_name": "Image Crop Sizes",
        "type": "manageable",
        "items": [
            {"is_active": True, "name": "4-3", "width": 800, "height": 600},
            {"is_active": True, "name": "16-9", "width": 1280, "height": 720}
        ]
    }

    def setUp(self):
        self.service = CropService()
        populate_table_json('vocabularies', [self.crop_sizes])

    def test_validate_aspect_ratio_fails(self):
        doc = {'CropLeft': 0, 'CropRight': 80, 'CropTop': 0, 'CropBottom': 60}
        crop = {'height': 700, 'width': 70}
        with assert_raises(SuperdeskApiError):
            self.service._validate_aspect_ratio(crop, doc)

    def test_validate_aspect_ratio_fails_with_cropsize_less(self):
        doc = {'CropLeft': 0, 'CropRight': 80, 'CropTop': 0, 'CropBottom': 60}
        crop = {'height': 600, 'width': 800}
        with assert_raises(SuperdeskApiError):
            self.service._validate_aspect_ratio(crop, doc)

    def test_validate_aspect_ratio_succeeds(self):
        doc = {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}
        crop = {'height': 600, 'width': 800}
        self.assertIsNone(self.service._validate_aspect_ratio(crop, doc))

    def test_validate_aspect_ratio_succeeds_2(self):
        doc = {'CropLeft': 0, 'CropRight': 1600, 'CropTop': 0, 'CropBottom': 1200}
        crop = {'height': 600, 'width': 800}
        self.assertIsNone(self.service._validate_aspect_ratio(crop, doc))

    def test_get_crop_by_name(self):
        self.assertIsNotNone(self.service.get_crop_by_name('16-9'))
        self.assertIsNotNone(self.service.get_crop_by_name('4-3'))
        self.assertIsNone(self.service.get_crop_by_name('d'))

    def test_validate_crop_raises_error_if_item_is_not_picture(self):
        original = {"type": "text"}
        doc = {'renditions': {'4-3': {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}}}
        with self.assertRaises(SuperdeskApiError) as context:
            self.service.validate_crop(original, doc, "4-3")

        ex = context.exception
        self.assertEqual(ex.message, 'Only images can be cropped!')
        self.assertEqual(ex.status_code, 400)

    def test_validate_crop_raises_error_if_renditions_are_missing(self):
        original = {"type": "picture"}
        doc = {'renditions': {'4-3': {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}}}
        with self.assertRaises(SuperdeskApiError) as context:
            self.service.validate_crop(original, doc, "4-3")

        ex = context.exception
        self.assertEqual(ex.message, 'Missing renditions!')
        self.assertEqual(ex.status_code, 400)

    def test_validate_crop_raises_error_if_original_rendition_is_missing(self):
        original = {"type": "picture",
                    "renditions": {"4-3": {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}}}
        doc = {'renditions': {'4-3': {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}}}
        with self.assertRaises(SuperdeskApiError) as context:
            self.service.validate_crop(original, doc, "4-3")

        ex = context.exception
        self.assertEqual(ex.message, 'Missing original rendition!')
        self.assertEqual(ex.status_code, 400)

    def test_validate_crop_raises_error_if_crop_name_is_unknown(self):
        original = {"type": "picture",
                    "renditions": {
                        "original": {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}
                    }
                    }
        doc = {'renditions': {'d': {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}}}
        with self.assertRaises(SuperdeskApiError) as context:
            self.service.validate_crop(original, doc, "d")

        ex = context.exception
        self.assertEqual(ex.message, 'Unknown crop name! (name=d)')
        self.assertEqual(ex.status_code, 400)

    def test_add_crop_raises_error_if_original_missing(self):
        original = {
            'renditions': {
                '4-3': {
                }
            }
        }
        doc = {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}
        with self.assertRaises(SuperdeskApiError) as context:
            self.service.create_crop(original, '4-3', doc)

        ex = context.exception
        self.assertEqual(ex.message, 'Original file couldn\'t be found')
        self.assertEqual(ex.status_code, 400)

    def test_validate_crop_converts_to_int(self):
        crop = {'width': '300', 'height': 200}
        self.service._validate_values(crop)
        self.assertEqual(300, crop['width'])
        self.assertEqual(200, crop['height'])

        with self.assertRaises(SuperdeskApiError) as context:
            self.service._validate_values({'width': 'foo'})
            self.assertEqual(context.exception.message, 'Invalid value for width in renditions')

    @mock.patch('superdesk.media.crop.crop_image', return_value=(False, 'test'))
    def test_add_crop_raises_error(self, crop_name):
        original = {
            'renditions': {
                'original': {
                }
            }
        }

        media = mock.MagicMock()
        media.name = 'test.jpg'

        with mock.patch('superdesk.app.media.get', return_value=media):
            doc = {'CropLeft': 0, 'CropRight': 800, 'CropTop': 0, 'CropBottom': 600}
            with self.assertRaises(SuperdeskApiError) as context:
                self.service.create_crop(original, '4-3', doc)

            ex = context.exception
            self.assertEqual(ex.message, 'Saving crop failed.')
            self.assertEqual(ex.status_code, 400)

    def test_crop_image_exact_size(self):
        img = get_picture_fixture()
        size = {'width': '300', 'height': '200'}
        crop = {'CropTop': '0', 'CropRight': '300', 'CropBottom': '200', 'CropLeft': '0'}
        with open(img, 'rb') as imgfile:
            res = crop_image(imgfile, img, crop, size)
            self.assertTrue(res[0])
            self.assertEqual(300, res[1].width)
            self.assertEqual(200, res[1].height)

    def test_resize_image(self):
        img = get_picture_fixture()
        with open(img, 'rb') as imgfile:
            resized, width, height = _resize_image(imgfile, ('200', None), 'jpeg')
            self.assertEqual(150, height)

    def test_get_rendition_spec_no_custom_crop(self):
        renditions = get_renditions_spec(no_custom_crops=True)
        for crop in self.crop_sizes.get('items'):
            self.assertNotIn(crop['name'], renditions)

    def test_get_rendition_spec_with_custom_crop(self):
        renditions = get_renditions_spec()
        for crop in self.crop_sizes.get('items'):
            self.assertIn(crop['name'], renditions)

    def test_can_generate_custom_crop_from_original(self):
        self.assertEquals(True, can_generate_custom_crop_from_original(800, 600, {'ratio': '16:9'}))
        self.assertEquals(True, can_generate_custom_crop_from_original(800, 600, {'width': 800, 'height': 600}))
        self.assertEquals(True, can_generate_custom_crop_from_original(810, 600, {'width': 800, 'height': 600}))
        self.assertEquals(True, can_generate_custom_crop_from_original(810, 610, {'width': 800, 'height': 600}))
        self.assertEquals(False, can_generate_custom_crop_from_original(780, 610, {'width': 800, 'height': 600}))
        self.assertEquals(False, can_generate_custom_crop_from_original(780, 590, {'width': 800, 'height': 600}))
        self.assertEquals(True, can_generate_custom_crop_from_original(780, 590, {'width': 800}))
        self.assertEquals(True, can_generate_custom_crop_from_original(780, 590, {'height': 800}))
        self.assertEquals(False, can_generate_custom_crop_from_original(780, 590, None))
