import importlib

update_module = importlib.import_module("superdesk.data_updates.00035_20250918-140342_users")


def test_forwards(app):
    app.data.insert(
        "users",
        [
            {
                "_id": "user1",
                "user_preferences": {"monitoring:view": {"allowed": True, "category": "news", "other_key": "value"}},
            }
        ],
    )
    data_update = update_module.DataUpdate()
    data_update.forwards(app.data.driver.db.users, app.data.driver.db)
    updated = app.data.find_one("users", req=None, _id="user1")
    assert "allowed" not in updated["user_preferences"]["monitoring:view"]
    assert "category" not in updated["user_preferences"]["monitoring:view"]
    assert updated["user_preferences"]["monitoring:view"].get("other_key") == "value"
