from datetime import datetime
from superdesk.tests import TestCase
from superdesk.commands.index_from_mongo import IndexFromMongo


class IndexFromMongoTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.data.pymongo("archive").db["archive"].insert_many(
            [
                {"_id": "1", "headline": "Old Archive", "_updated": datetime(2025, 1, 1, 5)},
                {"_id": "2", "headline": "New Archive", "_updated": datetime(2025, 1, 1, 10)},
            ]
        )

    async def test_index_from_mongo_with_date(self):
        def query_elastic():
            return self.app.data.elastic.search({"query": {"match_all": {}}}, "archive")

        resp = query_elastic()
        assert resp.count() == 0

        kwargs = {
            "collection_name": "archive",
            "all_collections": False,
            "page_size": None,
            "last_id": None,
            "string_id": None,
        }

        await IndexFromMongo().run(**kwargs, date="2025-01-02")

        resp = query_elastic()
        assert resp.count() == 0

        await IndexFromMongo().run(**kwargs, date="2025-01-01T08:00")

        resp = query_elastic()
        assert resp.count() == 1

        await IndexFromMongo().run(**kwargs, date="2025-01-01")

        resp = query_elastic()
        assert resp.count() == 2

        with self.assertRaises(ValueError):
            await IndexFromMongo().run(**kwargs, date="2025")
