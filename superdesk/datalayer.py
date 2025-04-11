# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import overload, Literal
from inspect import isawaitable

import superdesk

from eve.io.base import DataLayer
from eve.io.mongo import Mongo
from eve.utils import ParsedRequest
from eve_elastic import Elastic, InvalidSearchString  # noqa
from superdesk.core import get_current_async_app, get_config
from superdesk.lock import lock, unlock
from superdesk.json_utils import SuperdeskJSONEncoder

from .eve_async import MongoAsync, ElasticAsync


class SuperdeskDataLayer(DataLayer):
    """Superdesk Data Layer.

    Implements eve data layer interface, is used to make eve work with superdesk service layer.
    It handles app initialization and later it forwards eve calls to respective service.
    """

    serializers = {}
    serializers.update(Mongo.serializers)
    serializers.update(
        {
            "datetime": Elastic.serializers["datetime"],
        }
    )

    def init_app(self, app):
        app.data = self  # app.data must be set for locks to work
        self.mongo = Mongo(app)
        self.mongo_async = MongoAsync(app)
        self.driver = self.mongo.driver
        self.storage = self.driver
        self.elastic = Elastic(
            app, serializer=SuperdeskJSONEncoder(), skip_index_init=True, retry_on_timeout=True, max_retries=3
        )
        self.elastic_async = ElasticAsync(
            app, serializer=SuperdeskJSONEncoder(), skip_index_init=True, retry_on_timeout=True, max_retries=3
        )

    def pymongo(self, resource=None, prefix=None):
        return self.mongo.pymongo(resource, prefix)

    async def init_elastic(self, app, raise_on_mapping_error=False):
        """Init elastic index.

        It will create index and put mapping. It should run only once so locks are in place.
        Thus mongo must be already setup before running this.
        """
        async with app.app_context():
            if lock("elastic", expire=10):
                try:
                    resources_indexed = get_current_async_app().elastic.init_all_indexes(
                        raise_on_mapping_error=raise_on_mapping_error
                    )
                    for resource in self.get_elastic_resources():
                        if resource in resources_indexed:
                            continue
                        self.elastic.init_index(resource, raise_on_mapping_error=raise_on_mapping_error)

                finally:
                    unlock("elastic")

    def find(self, resource, req, lookup, perform_count=True):
        cursor = superdesk.get_resource_service(resource).get(req=req, lookup=lookup)
        if perform_count:
            return cursor, cursor.count()
        return cursor, None

    async def find_async(self, resource, req, lookup, perform_count=True):
        service = superdesk.get_resource_service(resource)

        if hasattr(service, "get_async"):
            cursor = await service.get_async(req=req, lookup=lookup)
        else:
            cursor = service.get(req=req, lookup=lookup)

        if perform_count:
            count = cursor.count()
            if isawaitable(count):
                count = await count
            return cursor, count
        return cursor, None

    def find_all(self, resource, max_results=1000):
        req = ParsedRequest()
        req.max_results = max_results
        cursor, _ = self._backend(resource).find(resource, req, None, perform_count=False)
        return cursor

    async def find_all_async(self, resource, max_results=1000):
        req = ParsedRequest()
        req.max_results = max_results
        cursor, _ = await self._backend(resource, use_async=True).find(resource, req, None, perform_count=False)
        return cursor

    def find_one(self, resource, req, check_auth_value=True, force_auth_field_projection=False, **lookup):
        item = superdesk.get_resource_service(resource).find_one(req=req, **lookup)
        if item is not None:
            item.setdefault("_type", self.datasource(resource)[0])
        return item

    async def find_one_async(self, resource, req, check_auth_value=True, force_auth_field_projection=False, **lookup):
        service = superdesk.get_resource_service(resource)

        if hasattr(service, "find_one_async"):
            item = await service.find_one_async(req=req, **lookup)
        else:
            item = service.find_one(req=req, **lookup)

        if item is not None:
            item.setdefault("_type", self.datasource(resource)[0])
        return item

    def find_one_raw(self, resource, _id):
        return self._backend(resource).find_one_raw(resource, _id)

    async def find_one_raw_async(self, resource, _id):
        return await self._backend(resource, use_async=True).find_one_raw(resource, _id)

    def find_list_of_ids(self, resource, ids, client_projection=None):
        return self._backend(resource).find_list_of_ids(resource, ids, client_projection)

    async def find_list_of_ids_async(self, resource, ids, client_projection=None):
        return self._backend(resource, use_async=True).find_list_of_ids(resource, ids, client_projection)

    def insert(self, resource, docs, **kwargs):
        return superdesk.get_resource_service(resource).create(docs, **kwargs)

    async def insert_async(self, resource, docs, **kwargs):
        service = superdesk.get_resource_service(resource)
        if hasattr(service, "create_async"):
            return await service.create_async(docs, **kwargs)
        return service.create(docs, **kwargs)

    def update(self, resource, id_, updates, original):
        return superdesk.get_resource_service(resource).update(id=id_, updates=updates, original=original)

    async def update_async(self, resource, id_, updates, original):
        service = superdesk.get_resource_service(resource)
        if hasattr(service, "update_async"):
            return await service.update_async(id=id_, updates=updates, original=original)
        return service.update(id=id_, updates=updates, original=original)

    def update_all(self, resource, query, updates):
        datasource = self.datasource(resource)
        driver = self._backend(resource).driver
        collection = driver.db[datasource[0]]
        return collection.update(query, {"$set": updates}, multi=True)

    async def update_all_async(self, resource, query, updates):
        datasource = self.datasource(resource)
        driver = self._backend(resource, use_async=True).driver
        collection = driver.db[datasource[0]]
        return collection.update(query, {"$set": updates}, multi=True)

    def replace(self, resource, id_, document, original):
        return superdesk.get_resource_service(resource).replace(id=id_, document=document, original=original)

    async def replace_async(self, resource, id_, document, original):
        service = superdesk.get_resource_service(resource)
        if hasattr(service, "replace_async"):
            return await service.replace_async(id=id_, document=document, original=original)
        return service.replace(id=id_, document=document, original=original)

    def remove(self, resource, lookup=None):
        if lookup is None:
            lookup = {}
        return superdesk.get_resource_service(resource).delete(lookup=lookup)

    async def remove_async(self, resource, lookup=None):
        if lookup is None:
            lookup = {}
        service = superdesk.get_resource_service(resource)
        if hasattr(service, "delete_async"):
            return await service.delete_async(lookup=lookup)
        return service.delete(lookup=lookup)

    def is_empty(self, resource):
        return self._backend(resource).is_empty(resource)

    async def is_empty_async(self, resource):
        return self._backend(resource, use_async=True).is_empty(resource)

    @overload
    def _search_backend(self, resource) -> Elastic | None:
        ...

    @overload
    def _search_backend(self, resource, use_async: Literal[False] = False) -> Elastic | None:
        ...

    @overload
    def _search_backend(self, resource, use_async: Literal[True]) -> ElasticAsync | None:
        ...

    def _search_backend(self, resource, use_async: bool = False) -> Elastic | ElasticAsync | None:
        if resource.endswith(get_config(str, "VERSIONS")):
            return None
        datasource = self.datasource(resource)
        try:
            backend = get_config(dict, "SOURCES", {})[datasource[0]]["search_backend"]
        except (KeyError, TypeError, AttributeError):
            backend = None

        if backend and use_async:
            backend += "_async"
        return getattr(self, backend) if backend is not None else None

    @overload
    def _backend(self, resource: str) -> Mongo | None:
        ...

    @overload
    def _backend(self, resource: str, use_async: Literal[False]) -> Mongo | None:
        ...

    @overload
    def _backend(self, resource: str, use_async: Literal[True]) -> MongoAsync | None:
        ...

    def _backend(self, resource: str, use_async: bool = False) -> Mongo | MongoAsync | None:
        datasource = self.datasource(resource)
        try:
            backend = get_config(dict, "SOURCES", {})[datasource[0]]["backend"]
        except (KeyError, TypeError, AttributeError):
            backend = "mongo"

        if use_async:
            backend += "_async"
        return getattr(self, backend)

    def get_mongo_collection(self, resource):
        return self.mongo.pymongo(resource).db[resource]

    def get_mongo_collection_async(self, resource):
        return self.mongo_async.pymongo(resource).db[resource]

    def get_elastic_resources(self):
        """Get set of available elastic resources."""
        resources = set()
        for resource in get_config(dict, "SOURCES", {}):
            datasource = self.datasource(resource)[0]
            if self._search_backend(datasource):
                resources.add(datasource)
        return resources
