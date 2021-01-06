from flask import json
from superdesk.tests import TestCase, setup_auth_user


class PaginationTestCase(TestCase):
    headers = [("Content-Type", "application/json")]

    def test_default_pagination(self):
        setup_auth_user(self)
        self.app.data.insert("stages", [{"name": "stage{}".format(i)} for i in range(300)])

        response = self.client.get("/api/stages", headers=self.headers)
        self.assertEqual(200, response.status_code)

        data = json.loads(response.get_data())
        self.assertEqual(200, len(data["_items"]))
        self.assertEqual(300, data["_meta"]["total"])
