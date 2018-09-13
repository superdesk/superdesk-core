
from superdesk.tests import TestCase
from superdesk import es_utils


class ESUtilsTestCase(TestCase):
    def test_filter2query(self):
        """Check that a saved_searches style filter is converted correctly to Elastic Search DSL"""
        filter_ = {"query": {"spike": "exclude", "notgenre": '["Article (news)"]'}}
        expected = {
            "query": {
                "bool": {
                    "must": [],
                    "must_not": [
                        {"term": {"state": "spiked"}},
                        {"term": {"package_type": "takes"}},
                    ],
                }
            },
            "post_filter": {
                "bool": {
                    "must": [],
                    "must_not": [{"terms": {"genre.name": ["Article (news)"]}}],
                }
            },
        }

        with self.app.app_context():
            query = es_utils.filter2query(filter_)
        self.assertEqual(query, expected)
