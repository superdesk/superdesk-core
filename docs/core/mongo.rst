.. core_mongo:

MongoDB
=======

.. module:: superdesk.core.mongo

MongoResources Instance
-----------------------
The :class:`MongoResources` instance provides access to the MongoDB resource configs,
client and database connections. This instance is available under the
:attr:`SuperdeskAsyncApp.mongo <superdesk.core.app.SuperdeskAsyncApp.mongo>` attribute.

There are two groups of functions to use: one for standard synchronous connections and another for asynchronous
connections. The functions ending in ``_async`` provide the asynchronous version.

For example::

    from superdesk.core.app import get_current_async_app

    def test():
        users = get_current_async_app().mongo.get_db("users")
        user = users.find_one({"_id": "abcd123"})

    async def test_async()
        users = get_current_async_app().mongo.get_db_async("users")
        user = await users.find_one({"_id": "abcd123"})


The :attr:`get_db <MongoResources.get_db>` method returns an instance of a
`PyMongo Database <https://pymongo.readthedocs.io/en/stable/api/pymongo/database.html>`_.

The :attr:`get_db_async <MongoResources.get_db_async>` method returns an instance of a
`Motor AsyncIOMotorDatabase <https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_database.html>`_.

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