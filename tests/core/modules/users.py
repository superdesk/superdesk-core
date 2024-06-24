from superdesk.core.module import Module, SuperdeskAsyncApp
from superdesk.core.mongo import MongoResourceConfig, MongoIndexOptions


user_mongo_resource = MongoResourceConfig(
    name="users",
    indexes=[
        MongoIndexOptions(
            name="users_name_1",
            keys=[("first_name", 1)],
        ),
        MongoIndexOptions(
            name="combined_name_1",
            keys=[("first_name", 1), ("last_name", -1)],
            background=False,
            unique=False,
            sparse=False,
            collation={"locale": "en", "strength": 1},
        ),
    ],
)


def init(app: SuperdeskAsyncApp):
    app.mongo.register_resource_config(user_mongo_resource)


module = Module(name="tests.users", init=init)
