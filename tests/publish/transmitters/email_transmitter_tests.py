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
from unittest.mock import Mock

from superdesk import json
from superdesk.publish.transmitters.email import EmailPublishService
from superdesk.tests import TestCase

MOCK_FILENAME = "IPTC-PhotometadataRef-Std2017.1.jpg"
MOCK_CONTENT_TYPE = "image/jpeg"


class MockMediaFS:
    """Simple Mocked Media FS"""

    def __init__(self):
        self.get = Mock()
        self.get.side_effect = self._get
        self.read = Mock()
        self.read.side_effect = self._read

    name = MOCK_FILENAME
    content_type = MOCK_CONTENT_TYPE

    def _get(self, id, resource):
        return self

    def _read(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", "IPTC-PhotometadataRef-Std2017.1.jpg"))
        with open(fixture, "rb") as f:
            return f.read()


class MockMail:
    def __init__(self):
        self.send = Mock()
        self.send.side_effect = self._send

    def _send(self, message):
        if message.subject != "Test Subject":
            raise ValueError("Unexpected Subjet")
        if len(message.attachments) != 1:
            raise Exception("Wrong number of attachments")


class EmailPublishServiceTest(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.media = MockMediaFS()

    async def test_attachment(self):
        item = {
            "message_text": "Test",
            "message_html": '<p>Test <img src="cid:MainImage"></p>',
            "message_subject": "Test Subject",
            "renditions": {"viewImage": {"media": "1234"}},
        }
        queue_item = {
            "item_id": "123",
            "destination": {
                "delivery_type": "email",
                "config": {
                    "media_cid": "MainImage",
                    "media_rendition": "viewImage",
                    "recipients": "a@b.c.d",
                    "attach_media": True,
                    "watermark": True,
                },
                "name": "Email",
                "format": "Email",
            },
            "formatted_item": json.dumps(item),
        }

        transmitter = EmailPublishService()
        with self.app.mail.record_messages() as outbox:
            await transmitter._transmit(queue_item=queue_item, subscriber={})
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, "Test Subject")
            self.assertIn('<img src="cid:MainImage">', outbox[0].html)

            # Get attachments from the message tree
            attachments: list[tuple[str, str, str]] = []
            for part in outbox[0].walk():
                content_id = part.get("Content-ID")
                if not content_id:
                    continue

                attachments.append((part.get_filename(), part.get_content_type(), content_id))

            self.assertEqual(attachments, [(MOCK_FILENAME, MOCK_CONTENT_TYPE, "<MainImage>")])
