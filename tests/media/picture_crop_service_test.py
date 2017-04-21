# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from io import BytesIO
from unittest import mock

from superdesk.tests import TestCase
from superdesk import get_resource_service
from ..media import get_picture_fixture

from apps.picture_crop import get_crop_size


def get_file_mock(rendition, item):
    filename = get_picture_fixture()
    with open(filename, 'rb') as imgfile:
        data = BytesIO(imgfile.read())
    return data


def crop_image_mock(content, file_name, cropping_data, exact_size=None, image_format=None):
    setattr(content, 'width', 1)
    setattr(content, 'height', 1)
    return True, content


def media_put_mock(content, filename=None, content_type=None, metadata=None, resource=None, **kwargs):
    media = mock.MagicMock()
    media.name = 'test.jpg'
    media.metadata = metadata
    return media


class PictureCropServiceTest(TestCase):
    @mock.patch('apps.picture_crop.get_file', side_effect=get_file_mock)
    @mock.patch('apps.picture_crop.crop_image', side_effect=crop_image_mock)
    @mock.patch('superdesk.app.media.put', side_effect=media_put_mock)
    def test_crop_image_copies_metadata(self, get_file_function, crop_image_function, media_put_function):
        service = get_resource_service('picture_crop')

        images = service.post([{
            'item': {
                'renditions': {
                    'original': {
                        'mimetype': 'image/jpeg'
                    }
                }
            },
            'crop': {
                'CropLeft': 10,
                'CropRight': 100,
                'CropTop': 10,
                'CropBottom': 100
            }
        }])

        self.assertEqual(images[0].metadata.get('datetime'), '"2015:07:06 16:30:23"')
        self.assertEqual(images[0].metadata.get('exifimagewidth'), '400')
        self.assertEqual(images[0].metadata.get('exifimageheight'), '300')

    def test_get_crop_size_fixes_crop_aspect_ratio(self):
        crop_data = {
            'CropLeft': 0,
            'CropRight': 1620,
            'CropTop': 0,
            'CropBottom': 1230,
            'width': 800,
            'height': 600
        }
        get_crop_size(crop_data)

        crop_width = crop_data['CropRight'] - crop_data['CropLeft']
        crop_height = crop_data['CropBottom'] - crop_data['CropTop']

        crop_ratio = crop_height / crop_width
        size_ratio = crop_data['height'] / crop_data['width']

        self.assertEqual(crop_ratio, size_ratio)
