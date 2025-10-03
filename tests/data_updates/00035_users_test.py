import importlib

from superdesk.tests import TestCase

update_module = importlib.import_module("superdesk.data_updates.00035_20250918-140342_users")


class DataUpdate00035UsersTestCase(TestCase):
    async def test_forwards(self):
        self.app.data.insert(
            "users",
            [
                {
                    "_id": "user1",
                    "user_preferences": {
                        "monitoring:view": {"allowed": True, "category": "news", "other_key": "value"}
                    },
                }
            ],
        )
        data_update = update_module.DataUpdate()
        data_update.forwards(self.app.data.driver.db.users, self.app.data.driver.db)
        updated = self.app.data.find_one("users", req=None, _id="user1")
        assert "allowed" not in updated["user_preferences"]["monitoring:view"]
        assert "category" not in updated["user_preferences"]["monitoring:view"]
        assert updated["user_preferences"]["monitoring:view"].get("other_key") == "value"
