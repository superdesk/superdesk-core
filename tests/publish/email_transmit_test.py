# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import mimetypes
from superdesk.publish.transmitters.email import EmailPublishService
from superdesk.tests import TestCase
from superdesk.publish import init_app
import os
from unittest.mock import Mock, call


class MockMediaFS:
    """Simple Mocked Media FS"""

    def __init__(self):
        self.get = Mock()
        self.get.side_effect = self._get
        self.read = Mock()
        self.read.side_effect = self._read

    name = 'filename'
    content_type = 'image/jpeg'

    def _get(self, id, resource):
        return self

    def _read(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, '../media/fixtures', 'IPTC-PhotometadataRef-Std2017.1.jpg'))
        with open(fixture, 'rb') as f:
            return f.read()


class MockMail:

    def __init__(self):
        self.send = Mock()
        self.send.side_effect = self._send

    def _send(self, message):
        if message.subject != 'Test Subject':
            raise ValueError('Unexpected Subjet')
        if len(message.attachments) != 1:
            raise Exception('Wrong number of attachments')


class EmailPublishServiceTest(TestCase):
    filename = "IPTC-PhotometadataRef-Std2017.1.jpg"

    def setUp(self):
        init_app(self.app)
        self._media = self.app.media
        self.app.media = MockMediaFS()
        self._mail = self.app.mail
        self.app.mail = MockMail()

    def tearDown(self):
        self.app.mail = self._mail
        self.app.media = self._media

    def test_attachment(self):
        queue_item = {
            'item_id': '123',
            'destination':
            {
                'delivery_type': 'email',
                'config': {
                    'media_cid': 'MainImage',
                    'media_rendition': 'viewImage',
                    'recipients': 'a@b.c.d',
                    'attach_media': True,
                    'watermark': True
                },
                'name': 'Email',
                'format': 'Email'
            },
            'formatted_item': '{"message_text": "Test", "message_html": "<p>Test</p>", '
                              '"message_subject": "Test Subject", "renditions": {"viewImage": {"media": "1234"}}}'
        }

        transmitter = EmailPublishService()
        transmitter._transmit(queue_item=queue_item, subscriber={})
