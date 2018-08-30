
from unittest import mock
from apps import saved_searches
from apps.saved_searches.saved_searches import encode_filter, decode_filter
from superdesk.tests import TestCase


class SavedSearchesTestCase(TestCase):
    def test_encode_decode_filter(self):
        data = {"foo": "bar"}
        encoded = encode_filter(data)
        self.assertEqual('{"foo": "bar"}', encoded)
        self.assertEqual('{"foo": "bar"}', encode_filter(encoded))
        decoded = decode_filter(encoded)
        self.assertEqual(data, decoded)
        self.assertEqual(data, decode_filter(decoded))

    @mock.patch.object(saved_searches, "send_report_email")
    def test_publish_report(self, send_report_email):
        """Check that publish_report is called correctly"""
        self.app.data.insert(
            "archive",
            [
                {
                    "_id": 1,
                    "guid": "#1",
                    "genre": {"name": "Article (news)", "qcode": "Article"},
                },
                {
                    "_id": 2,
                    "guid": "#2",
                    "genre": {"name": "Feature", "qcode": "Feature"},
                },
            ],
        )
        search_data = {
            "_id": "5b7ebf9b0d6f13085d4bf733",
            "name": "test_saved_search",
            "description": "test",
            "is_global": True,
            "filter": (
                '{"query": {"spike": "exclude", "repo": "archive,published,ingest,archived",'
                '"notgenre": "[\\"Article (news)\\"]"}}'
            ),
            "_updated": "2018-09-10 16:45:05+00:00",
            "_created": "2018-08-23 14:07:23+00:00",
            "user": "5b56e807cc3a2d1626a0507d",
            "_etag": "33227606e4403642083da966bfddf0fa056c81b1",
            "subscribers": {
                "user_subscriptions": [
                    {
                        "user": "5b56e807cc3a2d1626a0507d",
                        "scheduling": "*/5 * * * *",
                        "next_report": "2018-09-10 16:50:00+00:00",
                        "last_report": "2018-09-10 16:45:04.704000+00:00",
                    }
                ]
            },
        }
        with self.app.app_context():
            saved_searches.publish_report("5b7ebf9b0d6f13085d4bf733", search_data)
        self.assertTrue(send_report_email.called)
        sent_docs = send_report_email.call_args[0][2]
        self.assertEqual(len(sent_docs), 1)
        self.assertEqual(sent_docs[0]["guid"], "#2")
