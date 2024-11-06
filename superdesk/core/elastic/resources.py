# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, List, Optional
from collections import OrderedDict
import logging

import simplejson as json
from bson import ObjectId, decimal128
from bson.dbref import DBRef
from elasticsearch import AsyncElasticsearch, Elasticsearch, JSONSerializer, TransportError
from elasticsearch.exceptions import NotFoundError, RequestError

from superdesk.core.errors import ElasticNotConfiguredForResource

from .mapping import get_elastic_mapping_from_model
from .common import ElasticResourceConfig, ElasticClientConfig, generate_index_name
from .sync_client import ElasticResourceClient
from .async_client import ElasticResourceAsyncClient
from .reindex import reindex

logger = logging.getLogger(__name__)


class Superdesk3JSONSerializer(JSONSerializer):
    """Customize the JSON serializer used in Elastic."""

    def default(self, value):
        """Convert mongo.ObjectId."""
        if isinstance(value, ObjectId):
            # BSON/Mongo ObjectId is rendered as a string
            return str(value)
        if callable(value):
            # when SCHEMA_ENDPOINT is active, 'coerce' rule is likely to
            # contain a lambda/callable which can't be jSON serialized
            # (and we probably don't want it to be exposed anyway). See #790.
            return "<callable>"
        if isinstance(value, DBRef):
            retval = OrderedDict()
            retval["$ref"] = value.collection
            retval["$id"] = str(value.id)
            if value.database:
                retval["$db"] = value.database
            return json.RawJSON(json.dumps(retval))
        if isinstance(value, decimal128.Decimal128):
            return str(value)
        return super(Superdesk3JSONSerializer, self).default(value)


class ElasticResources:
    _elastic_connections: Dict[str, Elasticsearch]
    _resource_clients: Dict[str, ElasticResourceClient]

    _elastic_async_connections: Dict[str, AsyncElasticsearch]
    _resource_async_clients: Dict[str, ElasticResourceAsyncClient]

    #: A reference back to the parent app, for configuration purposes
    app: "SuperdeskAsyncApp"

    def __init__(self, app: "SuperdeskAsyncApp"):
        self._elastic_connections = {}
        self._resource_clients = {}

        self._elastic_async_connections = {}
        self._resource_async_clients = {}

        self.app = app

    def register_resource_config(
        self,
        resource_name: str,
        resource_config: ElasticResourceConfig,
    ):
        """Register a resource for use with Elasticsearch.

        :param resource_name: The name of the resource to register.
        :param resource_config: The config of the resource to register.
        """

        if resource_name in self._resource_clients:
            raise KeyError(f"ElasticResource '{resource_name}' already registered")

        client_config = ElasticClientConfig.create_from_dict(
            self.app.wsgi.config, prefix=resource_config.prefix or "ELASTICSEARCH", freeze=False
        )
        source_name = self.app.resources.get_config(resource_name).datasource_name or resource_name
        client_config.index += f"_{source_name}"
        client_config.set_frozen(True)

        self._resource_clients[resource_name] = ElasticResourceClient(source_name, client_config, resource_config)
        self._resource_async_clients[resource_name] = ElasticResourceAsyncClient(
            source_name, client_config, resource_config
        )

    def get_client(self, resource_name) -> ElasticResourceClient:
        """Get a synchronous ElasticResourceClient for a registered resource

        :param resource_name: The name of the resource to register.
        :return: A client used for managing resources
        :raises KeyError: If the resource is not registered for use with Elasticsearch
        """

        resource_client = self._resource_clients[resource_name]
        config = self.app.resources.get_config(resource_name)
        if config.elastic is None:
            raise KeyError(f"Elasticsearch not enabled on resource '{resource_name}'")
        config_prefix = config.elastic.prefix

        if not self._elastic_connections.get(config_prefix):
            self._elastic_connections[config_prefix] = Elasticsearch(
                [resource_client.config.url],
                serializer=Superdesk3JSONSerializer(),
                retry_on_timeout=resource_client.config.retry_on_timeout,
                max_retries=resource_client.config.max_retries,
                **(resource_client.config.options or {}),
            )

        self._resource_clients[resource_name].elastic = self._elastic_connections[config_prefix]
        return self._resource_clients[resource_name]

    def get_client_async(self, resource_name) -> ElasticResourceAsyncClient:
        """Get an asynchronous ElasticResourceAsyncClient for a registered resource

        :param resource_name: The name of the resource to register.
        :return: A client used for managing resources
        :raises KeyError: If the resource is not registered for use with Elasticsearch
        """

        try:
            resource_client = self._resource_async_clients[resource_name]
        except KeyError:
            raise ElasticNotConfiguredForResource(resource_name)

        config = self.app.resources.get_config(resource_name)
        if config.elastic is None:
            raise ElasticNotConfiguredForResource(resource_name)
        config_prefix = config.elastic.prefix

        if not self._elastic_async_connections.get(config_prefix):
            self._elastic_async_connections[config_prefix] = AsyncElasticsearch(
                [resource_client.config.url],
                serializer=Superdesk3JSONSerializer(),
                retry_on_timeout=resource_client.config.retry_on_timeout,
                max_retries=resource_client.config.max_retries,
                **(resource_client.config.options or {}),
            )

        self._resource_async_clients[resource_name].elastic = self._elastic_async_connections[config_prefix]
        return self._resource_async_clients[resource_name]

    async def close_all_clients(self):
        """Close all connections to Elasticsearch"""

        for client in self._elastic_connections.values():
            client.close()

        for client in self._elastic_async_connections.values():
            await client.close()

        self._elastic_connections.clear()
        self._elastic_async_connections.clear()

    async def stop(self):
        """Close all connections to Elasticsearch and clear all registrations"""

        await self.close_all_clients()
        self._elastic_connections.clear()
        self._resource_clients.clear()
        self._elastic_async_connections.clear()
        self._resource_async_clients.clear()

    async def reset_all_async_connections(self):
        for client in self._elastic_async_connections.values():
            await client.close()
        self._elastic_async_connections.clear()
        for config in self.app.resources.get_all_configs():
            self.get_client_async(config.name)

    def init_index(self, resource_name: str, raise_on_mapping_error: bool = False):
        """Init an Elasticsearch index for the provided resource

        :param resource_name: The name of the registered resource to init
        :param raise_on_mapping_error: If `True` will raise an exception if the mapping is invalid
        :raises KeyError: If the resource is not registered for use with Elasticsearch
        """

        resource_client = self.get_client(resource_name)

        try:
            if not resource_client.elastic.indices.exists(index=resource_client.config.index):
                self._create_index_from_alias(resource_client)
            elif resource_client.config.settings:
                self._put_settings(resource_client)

            mapping = get_elastic_mapping_from_model(
                resource_name,
                self.app.resources.get_config(resource_name).data_class,
                self.app.wsgi.config.get("SCHEMA_UPDATE", {}).get(resource_name),
            )
            resource_client.elastic.indices.put_mapping(index=resource_client.config.index, body=mapping)
        except RequestError:
            if self.app.wsgi.config.get("DEBUG") or raise_on_mapping_error:
                raise
            logger.warning(f"mapping error, updating settings resource={resource_name}")

    def init_all_indexes(self, raise_on_mapping_error=False) -> List[str]:
        """Init Elasticsearch indexes for all registered resources

        :param raise_on_mapping_error: If `True` will raise an exception if the mapping is invalid
        """

        resources_indexed: List[str] = []
        for config in self.app.resources.get_all_configs():
            if config.elastic is None:
                continue
            self.init_index(config.name, raise_on_mapping_error)
            resources_indexed.append(config.name)
        return resources_indexed

    def drop_indexes(self, index_prefix: str | None = None):
        """
        Drops Elasticsearch indexes for all registered resources. If `index_prefix` is provided
        then it will only drop the indexes that contain such prefix.
        """

        for config in self.app.resources.get_all_configs():
            if config.elastic is None:
                # Elasticsearch is not configured for this resource
                continue

            resource_client = self.get_client(config.name)
            index_alias = resource_client.config.index

            # skip if resource does not belong the provided index
            if index_prefix and index_alias != f"{index_prefix}_{config.name}":
                continue

            delete_index_fn = resource_client.elastic.indices.delete
            try:
                alias_info = resource_client.elastic.indices.get_alias(name=index_alias)
                for index in alias_info:
                    print(f"- Removing index alias={index_alias} index={index}")
                    delete_index_fn(index=index)
            except NotFoundError:
                try:
                    delete_index_fn(index=index_alias)
                except NotFoundError:
                    pass

    def _create_index_from_alias(self, resource_client: ElasticResourceClient):
        try:
            index = generate_index_name(resource_client.config.index)
            resource_client.elastic.indices.create(
                index=index, body={} if not resource_client.config.settings else resource_client.config.settings
            )
            resource_client.elastic.indices.put_alias(index=index, name=resource_client.config.index)
            logger.info(f"- Created index alias={resource_client.config.index} index={index}")
        except TransportError:  # index exists
            pass

    def get_settings(self, resource_client: ElasticResourceClient) -> Dict[str, Any]:
        """Get the settings from Elasticsearch for a registered resource

        :param resource_client: An ElasticResourceClient instance used to get the settings for
        :raises KeyError: If the resource is not registered for use with Elasticsearch
        """

        settings = resource_client.elastic.indices.get_settings(index=resource_client.config.index)
        return next(iter(settings.values()))

    def put_settings(self, resource_client: ElasticResourceClient):
        """Uploads the settings to Elasticsearch for a registered resource

        :param resource_client: An ElasticResourceClient instance used to upload the settings to
        """

        if not resource_client.config.settings:
            return

        try:
            old_settings = self.get_settings(resource_client)
            if _test_settings_contain(old_settings["settings"]["index"], resource_client.config.settings["settings"]):
                return
        except KeyError:
            pass

        self._put_settings(resource_client)

    def _put_settings(self, resource_client: ElasticResourceClient):
        """Modify index settings"""

        resource_client.elastic.indices.close(index=resource_client.config.index)
        resource_client.elastic.indices.put_settings(
            index=resource_client.config.index, body=resource_client.config.settings or {}
        )
        resource_client.elastic.indices.open(index=resource_client.config.index)

    def search(self, resource_names: List[str], query: Dict[str, Any]) -> Dict[str, Any]:
        """Search Elasticsearch across multiple indexes

        :param resource_names: A list of names of the registered resources to search in
        :param query: The search query to filter items by
        :return: A dictionary containing the results of the search
        :raises ValueError: If no registered resources found
        :raises ValueError: If the search is destined for different Elasticsearch clusters
        :raises KeyError: If any provided resource name is not registered for use with Elasticsearch
        """

        resource_configs = set(
            [
                config.elastic.prefix
                for config in self.app.resources.get_all_configs()
                if config.elastic is not None and config.name in resource_names
            ]
        )

        if len(resource_configs) == 0:
            raise ValueError("Resources not found")
        if len(resource_names) > 1:
            raise ValueError("Multiple prefixes found, searching multiple clusters not supported")

        client = self.get_client(resource_names[0])
        indexes = [self.get_client(resource_name).config.index for resource_name in resource_names]
        return client.search(query, indexes)

    async def search_async(self, resource_names: List[str], query: Dict[str, Any]) -> Dict[str, Any]:
        """Search Elasticsearch across multiple indexes

        :param resource_names: A list of names of the registered resources to search in
        :param query: The search query to filter items by
        :return: A dictionary containing the results of the search
        :raises ValueError: If no registered resources found
        :raises ValueError: If the search is destined for different Elasticsearch clusters
        :raises KeyError: If any provided resource name is not registered for use with Elasticsearch
        """

        resource_configs = set(
            [
                config.elastic.prefix
                for config in self.app.resources.get_all_configs()
                if config.elastic is not None and config.name in resource_names
            ]
        )

        if len(resource_configs) == 0:
            raise ValueError("Resources not found")
        if len(resource_names) > 1:
            raise ValueError("Multiple prefixes found, searching multiple clusters not supported")

        client = self.get_client_async(resource_names[0])
        indexes = [self.get_client(resource_name).config.index for resource_name in resource_names]
        return await client.search(query, indexes)

    def find_by_id(self, item_id: str, resource_names: List[str]) -> Optional[Dict[str, Any]]:
        """Find a document in multiple registered resources and Elasticsearch indexes

        :param item_id: The id of the item to find
        :param resource_names: A list of names of the registered resources to search in
        :return: The document if found, else None
        :raises KeyError: If any provided resource name is not registered for use with Elasticsearch
        """

        for resource_name in resource_names:
            doc = self.get_client(resource_name).find_by_id(item_id)
            if doc:
                return doc

        return None

    async def find_by_id_async(self, item_id: str, resource_names: List[str]) -> Optional[Dict[str, Any]]:
        """Find a document in multiple registered resources and Elasticsearch indexes

        :param item_id: The id of the item to find
        :param resource_names: A list of names of the registered resources to search in
        :return: The document if found, else None
        :raises KeyError: If any provided resource name is not registered for use with Elasticsearch
        """

        for resource_name in resource_names:
            doc = await self.get_client_async(resource_name).find_by_id(item_id)
            if doc:
                return doc

        return None

    def reindex(self, resource_name: str, *, requests_per_second: int = 1000):
        """Reindex a registered resource in Elasticsearch

        :param resource_name: The name of the registered resource to reindex
        :param requests_per_second: The number of requests to reindex per second
        :raises KeyError: If the resource is not registered for use with Elasticsearch
        """

        reindex(
            self.get_client(resource_name),
            get_elastic_mapping_from_model(
                resource_name,
                self.app.resources.get_config(resource_name).data_class,
                self.app.wsgi.config.get("SCHEMA_UPDATE", {}).get(resource_name),
            ),
            requests_per_second,
        )


def _test_settings_contain(current_settings: Dict[str, Any], new_settings: Dict[str, Any]) -> bool:
    """Test if current settings contain everything from new settings."""
    try:
        for key, val in new_settings.items():
            if isinstance(val, dict):
                if not _test_settings_contain(current_settings[key], val):
                    return False
            elif val != current_settings[key]:
                return False
        return True
    except KeyError:
        return False


from ..app import SuperdeskAsyncApp  # noqa: E402
