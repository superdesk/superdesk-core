.. core_elastic:

Elasticsearch
=============

.. module:: superdesk.core.elastic

ElasticResources Instance
-------------------------
The :class:`ElasticResources <resources.ElasticResources>` instance provides access to the Elasticsearch clients.
This instance is available under the :attr:`SuperdeskAsyncApp.elastic <superdesk.core.app.SuperdeskAsyncApp.elastic>`.

There are two types of clients you can use: one for standard synchronous connections and another for asynchronous
connections. The functions ending in ``_async`` provide the asynchronous version.

For example::

    from superdesk.core.app import get_current_async_app

    def test():
        client = get_current_async_app().elastic.get_client("users")
        users = client.search(
            {"query": {"term": {"first_name": "monkey"}}}
        )

    async def test_async():
        client = get_current_async_app().elastic.get_client_async("users")
        users = await client.search(
            {"query": {"term": {"first_name": "monkey"}}}
        )

The :attr:`get_client <resources.ElasticResources.get_client>` method returns an instance of
:class:`ElasticResourceClient <sync_client.ElasticResourceClient>`.

The :attr:`get_client_async <resources.ElasticResources.get_client>` method returns an instance of
:class:`ElasticResourceAsyncClient <async_client.ElasticResourceAsyncClient>`.


Elastic References
------------------
.. autoclass:: superdesk.core.elastic.common.SearchArgs
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.elastic.common.SearchRequest
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.elastic.common.ElasticResourceConfig
    :member-order: bysource
    :members:

.. autodata:: superdesk.core.elastic.common.ProjectedFieldArg

.. autoclass:: superdesk.core.elastic.resources.ElasticResources
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.elastic.sync_client.ElasticResourceClient
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.elastic.async_client.ElasticResourceAsyncClient
    :member-order: bysource
    :members:

.. autofunction:: superdesk.core.elastic.mapping.json_schema_to_elastic_mapping

.. autofunction:: superdesk.core.elastic.mapping.get_elastic_mapping_from_model
