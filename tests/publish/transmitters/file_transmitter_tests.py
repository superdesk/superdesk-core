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
from superdesk.publish import SUBSCRIBER_TYPES

from superdesk.tests import TestCase
from superdesk.publish.transmitters.file_output import FilePublishService
from superdesk.errors import PublishFileError


class FilePublishServiceTest(TestCase):
    def setUp(self):
        self.fixtures = os.path.join(os.path.abspath(os.path.dirname(__file__)))
        self.subscribers = [
            {
                "_id": "1",
                "name": "Test",
                "media_type": "media",
                "subscriber_type": SUBSCRIBER_TYPES.WIRE,
                "is_active": True,
                "sequence_num_settings": {"max": 10, "min": 1},
                "destinations": [
                    {"name": "test", "delivery_type": "File", "format": "nitf", "config": {"file_path": self.fixtures}}
                ],
            }
        ]

    def test_file_write(self):
        item = {
            "item_id": "test_file_name",
            "item_version": 1,
            "published_seq_num": 1,
            "formatted_item": "I was here",
            "encoded_item": b"I was here",
            "item_encoding": "utf-8",
            "destination": {
                "name": "test",
                "delivery_type": "File",
                "format": "nitf",
                "config": {"file_path": self.fixtures, "file_extension": "txt"},
            },
        }
        service = FilePublishService()
        try:
            service._transmit(item, self.subscribers)
            self.assertTrue(True)
        finally:
            path = os.path.join(self.fixtures, "test_file_name-1-1.txt")
            if os.path.isfile(path):
                os.remove(path)

    def test_format_default_file_extension(self):
        item = {
            "item_id": "test_file_name",
            "item_version": 1,
            "published_seq_num": 1,
            "formatted_item": "I was here",
            "encoded_item": b"I was here",
            "item_encoding": "utf-8",
            "destination": {
                "name": "test",
                "delivery_type": "File",
                "format": "nitf",
                "config": {"file_path": self.fixtures},
            },
        }
        service = FilePublishService()
        try:
            service._transmit(item, self.subscribers)
            self.assertTrue(True)
        finally:
            path = os.path.join(self.fixtures, "test_file_name-1-1.ntf")
            if os.path.isfile(path):
                os.remove(path)

        item["destination"]["config"]["file_extension"] = ""
        try:
            service._transmit(item, self.subscribers)
            self.assertTrue(True)
        finally:
            path = os.path.join(self.fixtures, "test_file_name-1-1.ntf")
            if os.path.isfile(path):
                os.remove(path)

    def test_file_write_fail(self):
        self.fixtures = os.path.join(os.path.abspath(os.path.dirname(__file__) + "/xyz"))
        item = {
            "item_id": "test_file_name",
            "item_version": 1,
            "formatted_item": "I was here",
            "encoded_item": b"I was here",
            "item_encoding": "utf-8",
            "destination": {
                "name": "test",
                "delivery_type": "File",
                "format": "nitf",
                "config": {"file_path": self.fixtures},
            },
        }

        with self.app.app_context():
            service = FilePublishService()
            try:
                service._transmit(item, self.subscribers)
            except PublishFileError as ex:
                self.assertEqual(str(ex), "PublishFileError Error 13000 - File publish error")
                self.assertEqual(ex.code, 13000)
