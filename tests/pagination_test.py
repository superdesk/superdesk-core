from superdesk.core import json
from superdesk.tests import TestCase, setup_auth_user, markers


class PaginationTestCase(TestCase):
    headers = [("Content-Type", "application/json")]

    @markers.requires_auth_headers_fix
    async def test_default_pagination(self):
        await setup_auth_user(self)
        self.app.data.insert("stages", [{"name": "stage{}".format(i)} for i in range(300)])

        response = await self.client.get("/api/stages", headers=self.headers)
        self.assertEqual(200, response.status_code)

        data = json.loads(await response.get_data())
        self.assertEqual(200, len(data["_items"]))
        self.assertEqual(300, data["_meta"]["total"])
