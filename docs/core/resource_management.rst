.. core_resource_management:

Resource Management
===================

Resource Services:
------------------

The management of resources is performed using the :class:`AsyncResourceService <superdesk.core.resources.service.AsyncResourceService>` class
instances. This is similar to how it is done in Superdesk < v3.0, with some slight improvements.

One major difference is the need to directly import the resource service from the module, and not use
`get_resource_service`. This gives us the full typed interface into the specifics of that resource.

For example::

    from my_module.users import UsersService, User

    async def test_users_service():
        service = UsersService()  # automatic singleton instance

        # Creat the user in both MongoDB and Elasticsearch
        await service.create([
            User(
                id="user_1",
                first_name="Monkey",
                last_name="Magic"
            )
        ])

        # Retrieve the user from the service
        my_user = await service.find_one(_id="user_1")
        assert my_user.first_name == "Monkey"

        # Update the user
        await service.update("user_1", {"last_name": "Mania"}

        # Find users
        cursor = service.search({
            "query": {
                "match": {
                    "first_name": "Monkey"
                }
            }
        })
        assert (await cursor.count()) == 1
        async for user in cursor:
            print(user)

        # Iterate over all users, in batches
        async for user in service.get_all_batch():
            print(user)

        # Delete the user from both MongoDB and Elasticsearch
        await service.delete({"_id": "user_1"})



Search References
-----------------
.. autoclass:: superdesk.core.resources.service.AsyncResourceService
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.resources.cursor.ResourceCursorAsync
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.resources.cursor.ElasticsearchResourceCursorAsync
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.resources.cursor.MongoResourceCursorAsync
    :member-order: bysource
    :members:
