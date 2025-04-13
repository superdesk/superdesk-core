from copy import deepcopy
from typing import Any

from superdesk.tests import AsyncFlaskTestCase, setup_auth_user, test_user


class PrivilegedResourceEndpointsTestCase(AsyncFlaskTestCase):
    use_default_apps = False
    app_config = {
        "MODULES": [
            "tests.core.modules.users",
            "tests.core.modules.module_with_privileges",
            "superdesk.users",
        ],
        "CORE_APPS": [
            "superdesk.activity",
            "apps.auth",
            "superdesk.users",
            "apps.auth.db",
            "superdesk.roles",
            "apps.preferences",
            "apps.stages",
        ],
    }

    async def _get_auth_token(self, user: dict[str, Any] | None = None):
        self.headers: list = []
        await setup_auth_user(self, user)

        auth_header = next((header for header in self.headers if header[0] == "Authorization"), None)
        if auth_header:
            return auth_header[1].replace("Basic", "Token")

        return ""

    async def _get_auth_header(self, user: dict[str, Any] | None = None) -> tuple:
        auth_token = await self._get_auth_token(user)
        return "Authorization", auth_token

    async def test_admin_can_access_privileged_endpoint(self):
        admin_user = deepcopy(test_user)
        admin_user["user_type"] = "administrator"

        headers = [await self._get_auth_header(admin_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)
        self.assertEqual(response.status_code, 200)

    async def test_unauthorized_user_cannot_access_privileged_endpoint(self):
        regular_user = deepcopy(test_user)
        regular_user["user_type"] = "user"

        headers = [await self._get_auth_header(regular_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)

        response_data = await response.get_json()
        self.assertEqual(response.status_code, 403, response_data)
        self.assertTrue("Insufficient privileges" in response_data["_message"])

    async def test_user_with_role_can_access_privileged_endpoint(self):
        from tests.core.modules.module_with_privileges import test_privileges

        can_read_privilege = test_privileges[0]
        roles = [{"name": "Can Read Role", "privileges": {can_read_privilege: 1}}]
        self.app.data.insert("roles", roles)

        regular_user = deepcopy(test_user)
        regular_user["user_type"] = "user"
        regular_user["role"] = roles[0]["_id"]

        headers = [await self._get_auth_header(regular_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)

        self.assertEqual(response.status_code, 200)

    async def test_cannot_access_endpoint_with_incorrect_privilege(self):
        from tests.core.modules.module_with_privileges import test_privileges

        can_create_privilege = test_privileges[1]
        can_create_only_role = {"name": "Can Read Role", "privileges": {can_create_privilege: 1}}
        self.app.data.insert("roles", [can_create_only_role])

        regular_user = deepcopy(test_user)
        regular_user["user_type"] = "user"
        regular_user["role"] = can_create_only_role["_id"]

        # user should not be able to "GET" as the role only has "POST" privilege
        headers = [await self._get_auth_header(regular_user)]
        response = await self.test_client.get("/api/privileged_resource", headers=headers)

        self.assertEqual(response.status_code, 403)
