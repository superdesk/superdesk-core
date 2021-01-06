import pytz
import flask
import base64
import unittest
import responses
import superdesk

from datetime import datetime, timedelta
from unittest.mock import patch
from tests.mock import resources
from superdesk.json_utils import SuperdeskJSONEncoder
from superdesk.publish.formatters.imatrics import IMatricsFormatter
from superdesk.publish.transmitters.imatrics import IMatricsTransmitter


class IMatricsTransmitterTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.config.update(
            {
                "IMATRICS_BASE_URL": "https://webdemo.imatrics.com/api/",
                "IMATRICS_USER": "foo",
                "IMATRICS_KEY": "key",
            }
        )

    @responses.activate
    def test_publish_article(self):
        start = datetime(2020, 10, 8, 10, 0, 0, tzinfo=pytz.UTC)
        with self.app.app_context():
            with patch.dict(superdesk.resources, resources):
                responses.add(
                    responses.POST,
                    url=self.app.config["IMATRICS_BASE_URL"] + "article/concept",
                    json={"uuid": "guid"},
                )
                formatter = IMatricsFormatter()
                subscriber = {}
                transmitter = IMatricsTransmitter()
                item = {
                    "guid": "guid",
                    "language": "en",
                    "pubstatus": "usable",
                    "abstract": "<p>foo bar baz</p>",
                    "dateline": {"text": "dateline.text"},
                    "firstcreated": start,
                    "versioncreated": start + timedelta(minutes=10),
                    "firstpublished": start + timedelta(minutes=20),
                    "headline": "headline <b>text</b>",
                    "body_html": "<p>foo bar baz</p><p>another one</p>",
                    "authors": [
                        {"sub_label": "john"},
                    ],
                    "subject": [
                        {
                            "name": "The category",
                            "scheme": "mediatopics",
                            "altids": {
                                "imatrics": "1",
                            },
                        },
                        {
                            "name": "A topic",
                            "scheme": "imatrics_topic",
                            "altids": {
                                "imatrics": "2",
                            },
                        },
                    ],
                    "organisation": [
                        {
                            "name": "An organisation",
                            "altids": {
                                "imatrics": "3",
                            },
                        },
                    ],
                    "person": [
                        {
                            "name": "A person",
                            "altids": {
                                "imatrics": "4",
                            },
                        },
                    ],
                    "place": [
                        {
                            "name": "A place",
                            "altids": {
                                "imatrics": "5",
                            },
                        },
                    ],
                    "event": [
                        {
                            "name": "An event",
                            "altids": {
                                "imatrics": "6",
                            },
                        },
                    ],
                    "object": [
                        {
                            "name": "An object",
                            "altids": {
                                "imatrics": "7",
                            },
                        },
                    ],
                }
                queue_item = {"formatted_item": formatter.format(item, subscriber)[0][1]}
                transmitter._transmit(queue_item, subscriber)
                self.assertEqual(len(responses.calls), 1)
                self.assertEqual(
                    "Basic {}".format(base64.b64encode("foo:key".encode()).decode()),
                    responses.calls[0].request.headers["Authorization"],
                )
                self.maxDiff = None
                self.assertEqual(
                    {
                        "uuid": "guid",
                        "language": "en",
                        "pubStatus": True,
                        "createdTimestamp": item["firstcreated"].isoformat(),
                        "latestVersionTimestamp": item["versioncreated"].isoformat(),
                        "publicationTimestamp": item["firstpublished"].isoformat(),
                        "authors": ["john"],
                        "concepts": [
                            {
                                "title": "The category",
                                "type": "category",
                                "uuid": "1",
                            },
                            {
                                "title": "A topic",
                                "type": "topic",
                                "uuid": "2",
                            },
                            {
                                "title": "An organisation",
                                "type": "organisation",
                                "uuid": "3",
                            },
                            {
                                "title": "A person",
                                "type": "person",
                                "uuid": "4",
                            },
                            {
                                "title": "A place",
                                "type": "place",
                                "uuid": "5",
                            },
                            {
                                "title": "An event",
                                "type": "event",
                                "uuid": "6",
                            },
                            {
                                "title": "An object",
                                "type": "object",
                                "uuid": "7",
                            },
                        ],
                        "headline": "headline text",
                        "preamble": "foo bar baz",
                        "dateline": "dateline.text",
                        "body": [
                            "foo bar baz",
                            "another one",
                        ],
                    },
                    flask.json.loads(responses.calls[0].request.body.decode()),
                )
