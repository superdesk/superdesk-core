# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
from unittest import TestCase
from superdesk.media.image import get_meta
from superdesk.media.media_operations import crop_image


fixtures = os.path.join(os.path.abspath(os.path.dirname(__file__)), "fixtures")


class ExifMetaExtractionTestCase(TestCase):

    img = os.path.join(fixtures, "canon_exif.JPG")

    def test_extract_meta_json_serialization(self):

        with open(self.img, mode="rb") as f:
            meta = get_meta(f)

        self.assertEqual(meta["ExifImageWidth"], 32)
        self.assertEqual(meta["ExifImageHeight"], 21)
        self.assertEqual(meta["Make"], "Canon")
        self.assertEqual(meta["Model"], "Canon EOS 60D")


class ExifMetaWithGPSInfoExtractionTestCase(TestCase):

    img = os.path.join(fixtures, "iphone_gpsinfo_exif.JPG")
    maxDiff = None

    def test_extract_meta_json_serialization(self):
        expected_gpsinfo = {
            "GPSImgDirection": 31.145,
            "GPSLongitudeRef": "W",
            "GPSImgDirectionRef": "T",
            "GPSAltitudeRef": 0,
            "GPSLatitudeRef": "S",
            "GPSAltitude": 576.978,
            "GPSLatitude": (33.0, 26.0, 11.5),
            "GPSLongitude": (70.0, 38.0, 39.46),
            "GPSTimeStamp": (19.0, 59.0, 51.17),
        }

        with open(self.img, mode="rb") as f:
            meta = get_meta(f)

        self.assertEqual(meta.get("ExifImageWidth", None), 400)
        self.assertEqual(meta.get("ExifImageHeight", None), 300)
        self.assertEqual(meta.get("Make", None), "Apple")
        self.assertEqual(meta.get("Model", None), "iPhone 5")
        self.assertEqual(meta.get("GPSInfo", None), expected_gpsinfo)


class ExifMetaExtractionUserCommentRemovedTestCase(TestCase):

    # this image has UserComment exif data value as 'test'
    img = os.path.join(fixtures, "iphone_gpsinfo_exif.JPG")

    def test_extract_meta_json_serialization(self):

        with open(self.img, mode="rb") as f:
            meta = get_meta(f)

        self.assertIsNone(meta.get("UserComment", None))


class MediaOperationsTestCase(TestCase):

    img = os.path.join(fixtures, "canon_exif.JPG")

    crop_data = {
        "CropLeft": 1,
        "CropTop": 1,
        "CropRight": 9,
        "CropBottom": 7,
    }

    def test_crop_image(self):
        with open(self.img, mode="rb") as f:
            status, output = crop_image(f, "test", self.crop_data)
            self.assertEqual(True, status)
            self.assertEqual(8, output.width)
            self.assertEqual(6, output.height)

    def test_crop_image_resize(self):
        with open(self.img, mode="rb") as f:
            status, output = crop_image(f, "test", self.crop_data, {"width": 4, "height": 3})
            self.assertEqual(True, status)
            self.assertEqual(4, output.width)
            self.assertEqual(3, output.height)
