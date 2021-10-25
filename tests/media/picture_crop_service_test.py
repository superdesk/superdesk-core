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
    with open(filename, "rb") as imgfile:
        data = BytesIO(imgfile.read())
    return data


def crop_image_mock(content, file_name, cropping_data, exact_size=None, image_format=None):
    setattr(content, "width", 1)
    setattr(content, "height", 1)
    return True, content


def media_put_mock(content, filename=None, content_type=None, metadata=None, resource=None, **kwargs):
    return "foo"


class PictureCropServiceTest(TestCase):
    @mock.patch("apps.picture_crop.get_file", side_effect=get_file_mock)
    @mock.patch("apps.picture_crop.crop_image", side_effect=crop_image_mock)
    def test_crop_image_copies_metadata(self, get_file_function, crop_image_function):
        service = get_resource_service("picture_crop")
        images = [
            {
                "item": {"renditions": {"original": {"mimetype": "image/jpeg"}}},
                "crop": {"CropLeft": 10, "CropRight": 100, "CropTop": 10, "CropBottom": 100},
            }
        ]

        with mock.patch.object(self.app.media, "put", return_value="foo"):
            service.post(images)

        self.assertEqual(images[0]["metadata"].get("datetime"), '"2015:07:06 16:30:23"')
        self.assertEqual(images[0]["metadata"].get("exifimagewidth"), "400")
        self.assertEqual(images[0]["metadata"].get("exifimageheight"), "300")

    def test_get_crop_size_fixes_crop_aspect_ratio(self):
        crop_data = {"CropLeft": 0, "CropRight": 1620, "CropTop": 0, "CropBottom": 1230, "width": 800, "height": 600}
        get_crop_size(crop_data)

        crop_width = crop_data["CropRight"] - crop_data["CropLeft"]
        crop_height = crop_data["CropBottom"] - crop_data["CropTop"]

        crop_ratio = crop_height / crop_width
        size_ratio = crop_data["height"] / crop_data["width"]

        self.assertEqual(round(crop_ratio, 3), round(size_ratio, 3))

    def test_get_crop_size_uses_full_picture(self):
        crop_data = {
            "width": 1290,
            "height": 490,
            "CropTop": 59,
            "CropRight": 1300,
            "CropBottom": 554,
            "CropLeft": 0,
        }

        crop_size = get_crop_size(crop_data)
        self.assertEqual(1290, crop_size["width"])
        self.assertEqual(490, crop_size["height"])
        self.assertEqual(0, crop_data["CropLeft"])
        self.assertEqual(1300, crop_data["CropRight"])
        self.assertEqual(59, crop_data["CropTop"])
        self.assertGreaterEqual(554, crop_data["CropBottom"])
