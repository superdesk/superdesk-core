# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import asyncio


class ClientMock:

    def __init__(self):
        self.messages = []
        self.client = None
        self.open = True

    @asyncio.coroutine
    def send(self, message):
        self.messages.append(message)
        yield from asyncio.sleep(0)

    def reset(self):
        self.messages = []


def setup_notification_mock(context):
    clientMock = ClientMock()
    if context.app.notification_client:
        clientMock.client = context.app.notification_client
    context.app.notification_client = clientMock


def teardown_notification_mock(context):
    context.app.notification_client = context.app.notification_client.client
