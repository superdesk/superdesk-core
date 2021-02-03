from superdesk.tests import TestCase
from superdesk import es_utils


class ESUtilsTestCase(TestCase):
    def test_filter2query(self):
        """Check that a saved_searches style filter is converted correctly to Elastic Search DSL"""
        filter_ = {"query": {"spike": "exclude", "notgenre": '["Article (news)"]'}}
        expected = {
            "query": {
                "bool": {"must": [], "must_not": [{"term": {"state": "spiked"}}, {"term": {"package_type": "takes"}}]}
            },
            "post_filter": {"bool": {"must": [], "must_not": [{"terms": {"genre.name": ["Article (news)"]}}]}},
            "sort": {"versioncreated": "desc"},
            "size": 10,
        }

        with self.app.app_context():
            query = es_utils.filter2query(filter_)
        self.assertEqual(query, expected)

    def test_filter2query_date(self):
        """Check that date a converted correctly to Elastic Search DSL"""
        filter_ = {
            "query": {
                "spike": "exclude",
                "firstcreatedfrom": "now-1M/M",
                "firstcreatedto": "now-1M/M",
                "firstpublished": "last_day",
                "versioncreatedfrom": "01/02/2018",
                "versioncreatedto": "11/12/2018",
            }
        }
        expected = {
            "query": {
                "bool": {"must": [], "must_not": [{"term": {"state": "spiked"}}, {"term": {"package_type": "takes"}}]}
            },
            "post_filter": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "firstcreated": {"lte": "now-1M/M", "gte": "now-1M/M"},
                                "versioncreated": {
                                    "lte": "2018-12-11T00:00:00+01:00",
                                    "gte": "2018-02-01T23:59:59.999999+01:00",
                                },
                                "firstpublished": {"lte": "now-1d/d", "gte": "now-1d/d"},
                            }
                        }
                    ],
                    "must_not": [],
                }
            },
            "sort": {"versioncreated": "desc"},
            "size": 10,
        }
        with self.app.app_context():
            query = es_utils.filter2query(filter_)
        self.assertEqual(query, expected)

    def test_filter2query_ingest_provider(self):
        """Check that ingest provider is handler correctly"""
        filter_ = {
            "query": {
                "repo": "ingest",
                "ingest_provider": "5c505c8f0d6f137d69cebc99",
                "spike": "exclude",
                "params": "{}",
            }
        }

        expected = {"bool": {"must": [{"term": {"ingest_provider": "5c505c8f0d6f137d69cebc99"}}], "must_not": []}}

        with self.app.app_context():
            query = es_utils.filter2query(filter_)

        self.assertEqual(query["post_filter"], expected)

    def test_filter2query_raw(self):
        filter_ = {
            "query": {
                "spike": "exclude",
                "raw": "headline:test",
            },
        }

        with self.app.app_context():
            query = es_utils.filter2query(filter_)

        self.assertIn(
            {
                "query_string": {
                    "query": "headline:test",
                    "lenient": False,
                    "default_operator": "AND",
                },
            },
            query["query"]["bool"]["must"],
        )

    def test_filter2query_priority(self):
        filter_ = {
            "query": {
                "priority": ["2"],
            },
        }

        with self.app.app_context():
            query = es_utils.filter2query(filter_)

        self.assertIn(
            {
                "terms": {
                    "priority": ["2"],
                },
            },
            query["post_filter"]["bool"]["must"],
        )

    def test_filter2repos_get_types(self):
        repos = es_utils.filter2repos({})
        self.assertIsNone(repos)
        types = es_utils.get_doc_types(repos)
        self.assertEqual(es_utils.REPOS, types)

        repos = es_utils.filter2repos({"query": {"repo": "ingest,published"}})
        self.assertEqual("ingest,published", repos)
        types = es_utils.get_doc_types(repos)
        self.assertEqual(["ingest", "published"], types)
