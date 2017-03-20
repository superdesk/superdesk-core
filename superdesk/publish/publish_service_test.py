# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from superdesk.publish import publish_service
from importlib import reload


class Base(TestCase):
    def setUpForChildren(self):
        super().setUpForChildren()

        reload(publish_service)
        self.service = publish_service.PublishService()
        self.fake_item = {
            "destination": {'format': 'nitf'},
            "item_id": "123:test_id-123",
            "item_version": "3",
            "published_seq_num": "5", }

    def fake_item_ext(self, format_):
        """Return a copy of self.fake_item with given destination/format"""
        item = self.fake_item.copy()
        item['destination'] = {'format': format_}
        return item


class FilenameTest(Base):
    def test_get_extension(self):
        nitf_ext = self.service.get_file_extension(self.fake_item_ext('nitf'))
        self.assertEqual(nitf_ext, 'ntf')
        xml_ext = self.service.get_file_extension(self.fake_item_ext('xml'))
        self.assertEqual(xml_ext, 'xml')
        ninjs_ext = self.service.get_file_extension(self.fake_item_ext('ninjs'))
        self.assertEqual(ninjs_ext, 'json')
        default_ext = self.service.get_file_extension(self.fake_item_ext('this_is_an_unknown_format'))
        self.assertEqual(default_ext, 'txt')
        # variant containing nitf must return nitf extension by default
        nitf_variant_ext = self.service.get_file_extension(self.fake_item_ext('nitf_variant'))
        self.assertEqual(nitf_variant_ext, 'ntf')

    def test_get_filename(self):
        filename = self.service.get_filename(self.fake_item)
        self.assertEqual(filename, "123-test_id-123-3-5.ntf")

    def test_get_filename_with_config(self):
        item = self.fake_item.copy()
        item['destination']['config'] = {'file_extension': 'test_ext'}
        filename = self.service.get_filename(item)
        self.assertEqual(filename, "123-test_id-123-3-5.test_ext")

    def test_get_filename_with_default_extension(self):
        item = self.fake_item.copy()
        item['destination'].pop('format', None)
        filename = self.service.get_filename(item)
        self.assertEqual(filename, "123-test_id-123-3-5.txt")


class FilenameCustomizedExtTest(Base):
    def setUp(self):
        self.service.register_file_extension("custom_format", "custom_ext")

    def test_get_extension(self):
        # is other file ext still working?
        nitf_ext = self.service.get_file_extension(self.fake_item_ext('nitf'))
        self.assertEqual(nitf_ext, 'ntf')
        # is the new one here ?
        custom_ext = self.service.get_file_extension(self.fake_item_ext('custom_format'))
        self.assertEqual(custom_ext, 'custom_ext')
        other_custom = self.service.get_file_extension(self.fake_item_ext('other_custom_format'))
        self.assertEqual(other_custom, 'custom_ext')

    def test_get_filename(self):
        filename = self.service.get_filename(self.fake_item_ext('custom_format'))
        self.assertEqual(filename, "123-test_id-123-3-5.custom_ext")
        filename = self.service.get_filename(self.fake_item)
        self.assertEqual(filename, "123-test_id-123-3-5.ntf")


class CustomizedService(publish_service.PublishServiceBase):

    @classmethod
    def get_filename(cls, queue_item):
        return "customized_filename.ext"


class FilenameCustomizedServiceTest(Base):
    def setUp(self):
        publish_service.set_publish_service(CustomizedService)
        self.service = publish_service.PublishService()

    def test_get_filename(self):
        filename = self.service.get_filename(self.fake_item)
        self.assertEqual(filename, "customized_filename.ext")
