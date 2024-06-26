.. core_mongo:

MongoDB
=======

MongoResources Instance
-----------------------
The :class:`MongoResources <mongo.MongoResources>` instance provides access to the MongoDB resource configs,
client and database connections. This instance is available under the :attr:`SuperdeskAsyncApp.mongo <app.SuperdeskAsyncApp.mongo>`
attribute.

There are 2 groups of functions to use. 1 for standard synchronous connections and another for asynchronous connections.
The functions ending in ``_async`` provide the asynchronous version.

For example::

    from superdesk.core.app import get_current_app

    def test():
        users = get_current_app().mongo.get_db("users")
        user = users.find_one({"_id": "abcd123"})

    async def test_async()
        users = get_current_app().mongo.get_db_async("users")
        user = await users.find_one({"_id": "abcd123"})


Registering Resources
---------------------
The :meth:`MongoResources.register_resource_config <mongo.MongoResources.register_resource_config>` method provides a way to
register resources for use with MongoDB, using :class:`MongoResourceConfig <mongo.MongoResourceConfig>` and
:class:`MongoIndexOptions <mongo.MongoIndexOptions>` classes.

The details of the registered resource is later used to create client connections,
create indexes etc for the specific resource. The :attr:`prefix <mongo.MongoResourceConfig.prefix>` config provides the same
``prefix`` capabilities to older style resources.

Example resource registration::

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


Mongo References
----------------
.. autoclass:: superdesk.core.mongo.MongoResourceConfig
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.mongo.MongoIndexOptions
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.mongo.MongoIndexCollation
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.mongo.MongoResources
    :member-order: bysource
    :members: