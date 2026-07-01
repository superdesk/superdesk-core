# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import io
import os
import hmac
import json
import re
import aiohttp
from aioresponses import aioresponses
from yarl import URL
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.publish.transmitters.http_push import HTTPPushService

from unittest import mock
from superdesk.errors import PublishHTTPPushServerError, PublishHTTPPushClientError
from superdesk.tests import TestCase


def get_fixture(fixture):
    filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../", "fixtures", "%s.json" % fixture)
    with open(filename, "r") as file:
        return json.load(file)


class ItemNotFound(Exception):
    pass


class NotFoundResponse:
    status_code = 404


class CreatedResponse:
    status_code = 201


class CreatedResponseSession:
    def send(self, request):
        self._request = request
        return CreatedResponse()


class TestMedia(io.BytesIO):
    _id = "media-id"
    filename = "foo.txt"
    mimetype = "text/plain"
    content_type = "text/plain"


class HTTPPushServiceTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        if "HTTP_PUSH_RESOURCE_URL" not in os.environ:
            self.resource_url = ""
        else:
            self.resource_url = os.environ["HTTP_PUSH_RESOURCE_URL"]

        self.subscribers = [
            {
                "_id": "1",
                "name": "Test",
                "media_type": "media",
                "subscriber_type": SUBSCRIBER_TYPES.DIGITAL,
                "is_active": True,
                "sequence_num_settings": {"max": 10, "min": 1},
                "destinations": [
                    {
                        "name": "test",
                        "delivery_type": "http_push",
                        "format": "ninjs",
                        "config": {"resource_url": self.resource_url, "secret_token": "123456789"},
                    }
                ],
            }
        ]
        self.formatted_item1 = {
            "_id": "item1",
            "headline": "headline",
            "versioncreated": "2015-03-09T16:32:23",
            "version": 1,
        }
        self.formatted_item2 = {
            "_id": "item1",
            "headline": "headline2",
            "versioncreated": "2015-03-21T13:43:51",
            "version": 2,
        }
        self.item = {
            "item_id": "item1",
            "format": "ninjs",
            "item_version": 1,
            "published_seq_num": 1,
            "formatted_item": json.dumps(self.formatted_item1),
            "destination": {
                "name": "test",
                "delivery_type": "http_push",
                "format": "ninjs",
                "config": {"resource_url": self.resource_url, "secret_token": "123456789"},
            },
        }

        self.destination = self.item.get("destination", {})

    @asynccontextmanager
    async def _get_item(self, item_id: str) -> AsyncIterator[aiohttp.ClientResponse]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.getItemURL(item_id)) as response:
                yield response

    async def is_item_published(self, item_id):
        """Return True if the item was published, False otherwise.

        Raises Exception in case of server/communication error.
        """
        if not getattr(self, "resource_url", None):
            return

        async with self._get_item(item_id) as response:
            if response.status == 404:
                return False
            self.assertEqual(response.status, 200, "Error retrieving item from the content API")
            return True

    def getItemURL(self, item_id):
        """Returns the URL for item read

        @param item_id: the item identifier
        @return: string
        """
        return "%s/%s" % (self.resource_url, item_id)

    def test_get_assets_url(self):
        service = HTTPPushService()
        self.assertEqual(service._get_assets_url(self.destination), None)

    def test_get_resource_url(self):
        service = HTTPPushService()
        self.assertEqual(service._get_resource_url(self.destination), self.resource_url)

    def test_get_secret_token(self):
        service = HTTPPushService()
        self.assertEqual(service._get_secret_token(self.destination), "123456789")

    async def test_get_headers(self):
        service = HTTPPushService()
        headers = await service._get_headers("test payload", self.destination, {})
        self.assertEqual("sha1=8be62a607898504f87559cb52dc23f9ebee65a21", headers[service.hash_header])

    async def test_publish_an_item(self):
        if not getattr(self, "resource_url", None):
            return

        service = HTTPPushService()

        await service._transmit(self.item, self.subscribers)
        self.assertTrue(self.is_item_published(self.item["item_id"]))

        self.item["formatted_item"] = json.dumps(self.formatted_item2)
        await service._transmit(self.item, self.subscribers)

        async with self._get_item(self.item["item_id"]) as response:
            item = await response.json()

        self.assertEqual(item["headline"], "headline2")
        self.assertEqual(item["version"], 2)

    @mock.patch("superdesk.errors.notifiers")
    async def test_client_publish_error_thrown(self, fake_notifiers):
        with aioresponses() as http_mock:
            http_mock.post(
                re.compile(".*"),
                status=401,
                body="client 4xx",
                exception=PublishHTTPPushClientError.httpPushError(Exception("client 4xx")),
            )

            # needed for bad exception handling classes
            fake_notifiers.return_value = []

            service = HTTPPushService()

            with self.assertRaises(PublishHTTPPushClientError):
                async with self.app.app_context():
                    await service._push_item(self.destination, json.dumps(self.item))

    @mock.patch("superdesk.errors.notifiers")
    async def test_server_publish_error_thrown(self, fake_notifiers):
        with aioresponses() as http_mock:
            http_mock.post(
                re.compile(".*"),
                status=503,
                body="server 5xx",
                exception=PublishHTTPPushServerError.httpPushError(Exception("server 5xx")),
            )

            # needed for bad exception handling classes
            fake_notifiers.return_value = []

            service = HTTPPushService()

            with self.assertRaises(PublishHTTPPushServerError):
                async with self.app.app_context():
                    await service._push_item(self.destination, json.dumps(self.item))

    async def test_push_associated_assets(self):
        with aioresponses() as http_mock:
            http_mock.get(re.compile(".*"), repeat=True, status=200, payload={})
            http_mock.post(re.compile(".*"), repeat=True, status=200, payload={})

            with mock.patch.object(self.app.media, "get", return_value=TestMedia(b"bin")):
                dest = {"config": {"assets_url": "http://example.com"}}
                item = get_fixture("package")

                service = HTTPPushService()
                await service._copy_published_media_files({}, dest)

                http_mock.assert_not_called()

                await service._copy_published_media_files(item, dest)

                images = [
                    # embedded original
                    "2017020111028/9a836848c3c3387a151dbed96e83b7d50e6b0e71ca397e0b1dc0f4b2f4127acd.jpg",
                    # main-0 original
                    "20170201110216/d3ad29bafe0710c42b7cfc201939f266c6ca5c11a713625388decff4da87ba5b.jpg",
                    # embedded thumbnail
                    "2017020111028/a0502320d6d07dd921253171e971943adf791eb2b34dfe82da73c053a343a7c2.jpg",
                ]

                for media in images:
                    http_mock.assert_called_with(f"http://example.com/{media}", method="GET")

    async def test_push_attachments(self):
        test_file = TestMedia(b"bin")

        with aioresponses() as http_mock:
            http_mock.get("http://example.com/media-id", repeat=True, status=404, payload={})
            http_mock.post("http://example.com", repeat=True, status=201, payload={})

            with mock.patch.object(self.app.media, "get") as media_mock:
                media_mock.return_value = test_file

                dest = {"config": {"assets_url": "http://example.com", "secret_token": "foo"}}
                item = {
                    "type": "text",
                    "attachments": [
                        {"id": "foo", "media": "media-id", "mimetype": "text/plain"},
                    ],
                }

                service = HTTPPushService()
                await service._copy_published_media_files(item, dest)

                media_mock.assert_called_with("media-id", resource="attachments")
                http_mock.assert_called_with("http://example.com/media-id", method="GET")

                post_requests = http_mock.requests[("POST", URL("http://example.com"))]
                self.assertEqual(len(post_requests), 1)

                request_body = post_requests[0].kwargs["data"]
                self.assertIsInstance(request_body, aiohttp.FormData)

                headers = post_requests[0].kwargs["headers"]
                request_body_bytes = await request_body().as_bytes()
                expected_hash = hmac.new(b"foo", request_body_bytes, "sha1")
                self.assertIn(b"bin", request_body_bytes)
                self.assertIn(b"media-id", request_body_bytes)
                self.assertEqual(headers["x-superdesk-signature"], f"sha1={expected_hash.hexdigest()}")

    async def test_push_binaries(self):
        media = TestMedia(b"content")
        dest = {"config": {"assets_url": "http://example.com", "secret_token": "foo"}}

        with aioresponses() as http_mock:
            http_mock.get("http://example.com/media-id", repeat=True, status=404, payload={})
            http_mock.post("http://example.com", repeat=True, status=201, payload={})

            service = HTTPPushService()
            await service._transmit_media(media, dest)

            http_mock.assert_called_with("http://example.com/media-id", method="GET")

            post_requests = http_mock.requests[("POST", URL("http://example.com"))]
            self.assertEqual(len(post_requests), 1)

            request_body = post_requests[0].kwargs["data"]
            self.assertIsInstance(request_body, aiohttp.FormData)
            self.assertIn(b"content", await request_body().as_bytes())
