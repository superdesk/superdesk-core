# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import random
from typing import (
    Optional,
    Generic,
    Sequence,
    TypeVar,
    ClassVar,
    List,
    Dict,
    Any,
    AsyncIterable,
    Union,
    cast,
    overload,
    Type,
)
import logging
import ast
import simplejson as json
from copy import deepcopy
from hashlib import sha1

from bson import ObjectId, UuidRepresentation
from bson.json_util import dumps, DEFAULT_JSON_OPTIONS
from motor.motor_asyncio import AsyncIOMotorCursor

from superdesk.core.types import SearchRequest, SortListParam, SortParam, ProjectedFieldArg
from superdesk.flask import g
from superdesk.utc import utcnow
from superdesk.cache import cache
from superdesk.errors import SuperdeskApiError
from superdesk.json_utils import SuperdeskJSONEncoder
from superdesk.resource_fields import ID_FIELD, VERSION_ID_FIELD, CURRENT_VERSION, LATEST_VERSION

from ..app import SuperdeskAsyncApp, get_current_async_app
from .cursor import ElasticsearchResourceCursorAsync, MongoResourceCursorAsync, ResourceCursorAsync
from .utils import get_projection_from_request

logger = logging.getLogger(__name__)


ResourceModelType = TypeVar("ResourceModelType", bound="ResourceModel")


class AsyncResourceService(Generic[ResourceModelType]):
    resource_name: ClassVar[str]
    config: "ResourceConfig"
    app: SuperdeskAsyncApp

    def __new__(cls):
        app = get_current_async_app()
        try:
            resource_config = app.resources.get_config(cls.resource_name)
        except KeyError:
            raise RuntimeError(f"AsyncResourceService {cls} is not registered with the App")

        instance = getattr(cls, "_instance", None)

        if instance is not None and instance.app != app:
            # The app has changed, need to recreate this service
            # This is only for test purposes when the app is re-created
            instance = None

        if not instance:
            instance = super(AsyncResourceService, cls).__new__(cls)
            instance.app = app
            instance.config = resource_config
            setattr(cls, "_instance", instance)

        return instance

    def id_uses_objectid(self) -> bool:
        return self.config.data_class.uses_objectid_for_id()

    @property
    def mongo(self):
        """Return instance of MongoCollection for this resource"""

        return self.app.mongo.get_collection(self.resource_name)

    @property
    def mongo_async(self):
        """Return instance of async MongoCollection for this resource"""

        return self.app.mongo.get_collection_async(self.resource_name)

    @property
    def mongo_versioned_async(self):
        return self.app.mongo.get_collection_async(self.resource_name, True)

    @property
    def elastic(self):
        """Returns instance of ``ElasticResourceAsyncClient`` for this resource

        :raises KeyError: If this resource is not configured for Elasticsearch
        """

        return self.app.elastic.get_client_async(self.resource_name)

    def get_model_instance_from_dict(self, data: Dict[str, Any]) -> ResourceModelType:
        """Converts a dictionary to an instance of ``ResourceModel`` for this resource

        :param data: Dictionary to convert
        :return: Instance of ``ResourceModel`` for this resource
        """

        # We can't use ``model_construct`` method to construct instance without validation
        # because nested models are not being converted to model instances
        return cast(ResourceModelType, self.config.data_class.from_dict(data))

    @overload
    async def find_one_raw(self, req: SearchRequest) -> dict | None:
        ...

    @overload
    async def find_one_raw(
        self,
        req: None = None,
        *,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
        version: int | None = None,
        **lookup,
    ) -> dict | None:
        ...

    async def find_one_raw(
        self,
        req: SearchRequest | None = None,
        *,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
        version: int | None = None,
        **lookup,
    ) -> dict | None:
        search_request = (
            req
            if req is not None
            else SearchRequest(
                where=lookup,
                page=1,
                max_results=1,
                projection=projection,
                use_mongo=use_mongo,
                version=version,
            )
        )

        if not search_request.projection and self.config.projection:
            search_request.projection = self.config.projection

        item = None
        try:
            if not search_request.use_mongo:
                item = await self.elastic.find_one(search_request)
        except KeyError:
            pass

        if search_request.use_mongo or item is None:
            kwargs = dict(
                filter=json.loads(search_request.where or "{}")
                if isinstance(search_request.where, str)
                else search_request.where or {}
            )
            projection_include, projection_fields = get_projection_from_request(search_request)
            if projection_fields:
                kwargs["projection"] = (
                    projection_fields if projection_include else {field: False for field in projection_fields}
                )
            mongo = self.mongo_async if not search_request.version else self.mongo_versioned_async
            item = await mongo.find_one(**kwargs)

        if item is None:
            return None
        elif search_request.version is not None:
            item = await self.get_item_version(item, search_request.version)

        return item

    @overload
    async def find_one(self, req: SearchRequest) -> ResourceModelType | None:
        ...

    @overload
    async def find_one(
        self,
        req: None = None,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
        version: int | None = None,
        **lookup,
    ) -> ResourceModelType | None:
        ...

    async def find_one(
        self,
        req: SearchRequest | None = None,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
        version: int | None = None,
        **lookup,
    ) -> ResourceModelType | None:
        if req is None:
            item = await self.find_one_raw(projection=projection, use_mongo=use_mongo, version=version, **lookup)
        else:
            item = await self.find_one_raw(req)
        return None if not item else self.get_model_instance_from_dict(item)

    async def find_by_id(
        self, item_id: Union[str, ObjectId], version: int | None = None
    ) -> Optional[ResourceModelType]:
        """Find a resource by ID

        :param item_id: ID of item to find
        :param version: Optional version to get
        :return: ``None`` if resource not found, otherwise an instance of ``ResourceModel`` for this resource
        """

        item = await self.find_by_id_raw(item_id, version)
        return None if item is None else self.get_model_instance_from_dict(item)

    async def find_by_id_raw(
        self, item_id: Union[str, ObjectId], version: int | None = None
    ) -> Optional[Dict[str, Any]]:
        """Find a resource by ID

        :param item_id: ID of item to find
        :param version: Optional version to get
        :return: ``None`` if resource not found, otherwise a dictionary of the item
        """

        item_id = ObjectId(item_id) if self.id_uses_objectid() else item_id
        try:
            item = await self.elastic.find_by_id(item_id)
        except KeyError:
            item = await self.mongo_async.find_one({"_id": item_id})

        if item is None:
            return None

        return item if version is None else await self.get_item_version(item, version)

    async def search(self, lookup: Dict[str, Any], use_mongo=False) -> ResourceCursorAsync[ResourceModelType]:
        """Search the resource using the provided ``lookup``

        Will use Elasticsearch if configured for this resource and ``use_mongo == False``.

        :param lookup: Dictionary to search
        :param use_mongo: Force to use MongoDB instead of Elasticsearch
        :return: A ``ResourceCursorAsync`` instance with the response
        """

        try:
            if not use_mongo:
                response = await self.elastic.search(lookup)
                return ElasticsearchResourceCursorAsync(cast(Type[ResourceModelType], self.config.data_class), response)
        except KeyError:
            pass

        response = self.mongo_async.find(lookup)
        return MongoResourceCursorAsync(
            cast(Type[ResourceModelType], self.config.data_class), self.mongo_async, response, lookup
        )

    async def on_create(self, docs: List[ResourceModelType]) -> None:
        """Hook to run before creating new resource(s)

        :param docs: List of resources to create
        """

        for doc in docs:
            if doc.created is None:
                doc.created = utcnow()
            if doc.updated is None:
                doc.updated = doc.created

    async def validate_create(self, doc: ResourceModelType):
        """Validate the provided doc for creation

        Runs the async validators

        :param doc: Model instance to validate
        :raises ValueError: If the item is not valid
        """

        await doc.validate_async()

    async def validate_update(
        self, updates: Dict[str, Any], original: ResourceModelType, etag: str | None
    ) -> Dict[str, Any]:
        """Validate the provided updates dict against the original model instance

        Applies the updates to a copy of the original provided, and runs sync and async validators

        :param updates: Dictionary of updates to be applied
        :param original: Model instance of the original item to be updated
        :param etag: Optional etag, if provided will check etag against original item
        :raises ValueError: If the item is not valid
        """

        self.validate_etag(original, etag)

        # Construct a new ResourceModelType instance, to allow Pydantic to validate the changes
        # This is not efficient, but will do for now
        updated = original.to_dict()
        updated.update(updates)
        updated.pop("_type", None)
        # Run the Pydantic sync validators, and get a model instance in return
        # Enable ``include_unknown`` so we get unknown field validation
        model_instance = self.config.data_class.from_dict(updated, include_unknown=True)

        # Run the async validators
        await model_instance.validate_async()

        # Re-dump the model for use with sending to MongoDB
        # This will make sure values are of correct type for MongoDB (such as ObjectId)
        return model_instance.to_dict(
            context={"use_objectid": True} if not self.config.query_objectid_as_string else {},
        )

    async def create(self, _docs: Sequence[ResourceModelType | dict[str, Any]]) -> List[str]:
        """Creates a new resource

        Will automatically create the resource(s) in both Elasticsearch (if configured for this resource)
        and MongoDB.

        :param docs: List of resources or dictionaries to create the registries
        :return: List of IDs for the created resources
        :raises Pydantic.ValidationError: If any of the docs provided are not valid
        """

        docs = self._convert_dicts_to_model(_docs)
        await self.on_create(docs)

        ids: List[str] = []

        for doc in docs:
            await self.validate_create(doc)
            versioned_model = get_versioned_model(doc)
            if versioned_model is not None:
                versioned_model.current_version = 1
            doc_dict = doc.to_dict(
                context={"use_objectid": True} if not self.config.query_objectid_as_string else {},
            )
            doc.etag = doc_dict["_etag"] = self.generate_etag(doc_dict, self.config.etag_ignore_fields)
            response = await self.mongo_async.insert_one(doc_dict)
            ids.append(response.inserted_id)
            try:
                await self.elastic.insert([doc_dict])
            except KeyError:
                pass

            if self.config.versioning:
                await self.insert_versioned_document(doc_dict)

        await self.on_created(docs)
        return ids

    async def insert_versioned_document(self, doc_dict: dict[str, Any]):
        await self.mongo_versioned_async.insert_one(self._get_versioned_document(doc_dict))

    def _get_versioned_document(self, doc_dict: dict[str, Any]) -> dict[str, Any]:
        versioned_doc = doc_dict.copy()
        versioned_doc["_id_document"] = versioned_doc.pop("_id", None)

        for field in self.config.ignore_fields_in_versions or []:
            versioned_doc.pop(field, None)

        return versioned_doc

    async def on_created(self, docs: List[ResourceModelType]) -> None:
        """Hook to run after creating new resource(s)

        :param docs: List of resources that were created
        """

        pass

    async def on_update(self, updates: Dict[str, Any], original: ResourceModelType) -> None:
        """Hook to run before updating a resource

        :param item_id: ID of item to update
        :param updates: Dictionary to update
        :param original: Instance of ``ResourceModel`` for the original resource
        """

        updates.setdefault("_updated", utcnow())
        versioned_original = get_versioned_model(original)
        if versioned_original:
            updates["_current_version"] = (versioned_original.current_version or 0) + 1

    async def update(self, item_id: Union[str, ObjectId], updates: Dict[str, Any], etag: str | None = None) -> None:
        """Updates an existing resource

        Will automatically update the resource in both Elasticsearch (if configured for this resource)
        and MongoDB.

        :param item_id: ID of item to update
        :param updates: Dictionary to update
        :param etag: Optional etag, if provided will check etag against original item
        :raises SuperdeskApiError.notFoundError: If original item not found
        """

        item_id = ObjectId(item_id) if self.id_uses_objectid() else item_id
        original = await self.find_by_id(item_id)
        if original is None:
            raise SuperdeskApiError.notFoundError()

        await self.on_update(updates, original)
        validated_updates = await self.validate_update(updates, original, etag)
        updates_dict = {key: val for key, val in validated_updates.items() if key in updates}
        updates["_etag"] = updates_dict["_etag"] = self.generate_etag(validated_updates, self.config.etag_ignore_fields)

        # Remove the ``_latest_version`` in case the client sent this to us
        # as we populate that on fetch of a version

        if model_has_versions(original):
            updates.pop("_latest_version", None)
            updates_dict.pop("_latest_version", None)
        response = await self.mongo_async.update_one({"_id": item_id}, {"$set": updates_dict})
        try:
            await self.elastic.update(item_id, updates_dict)
        except KeyError:
            pass

        if self.config.versioning:
            await self.mongo_versioned_async.insert_one(self._get_versioned_document(validated_updates))

        await self.on_updated(updates, original)

    async def on_updated(self, updates: Dict[str, Any], original: ResourceModelType) -> None:
        """Hook to run after a resource has been updated

        :param updates: Dictionary to update
        :param original: Instance of ``ResourceModel`` for the original resource
        """

        pass

    async def on_delete(self, doc: ResourceModelType):
        """Hook to run before deleting a resource

        :param doc: Instance of ``ResourceModel`` for the resource to delete
        """

        pass

    async def delete(self, doc: ResourceModelType, etag: str | None = None):
        """Deletes a resource

        :param doc: Instance of ``ResourceModel`` for the resource to delete
        :param etag: Optional etag, if provided will check etag against original item
        """

        await self.on_delete(doc)
        self.validate_etag(doc, etag)
        await self.mongo_async.delete_one({"_id": doc.id})
        try:
            await self.elastic.remove(doc.id)
        except KeyError:
            pass
        await self.on_deleted(doc)

    async def delete_many(self, lookup: Dict[str, Any]) -> List[str]:
        """Deletes resource(s) using a lookup

        :param lookup: Dictionary for the lookup to find items to delete
        :return: List of IDs for the deleted resources
        """

        docs_to_delete = self.mongo_async.find(lookup).sort("_id", 1)
        ids: List[str] = []

        async for data in docs_to_delete:
            doc = self.get_model_instance_from_dict(data)
            await self.on_delete(doc)
            ids.append(str(doc.id))
            await self.mongo_async.delete_one({"_id": doc.id})

            if self.config.versioning:
                await self.mongo_versioned_async.delete_many({VERSION_ID_FIELD: doc.id})

            try:
                await self.elastic.remove(doc.id)
            except KeyError:
                pass

            await self.on_deleted(doc)
        return ids

    async def on_deleted(self, doc: ResourceModelType):
        """Hook to run after deleting a resource

        :param doc: Instance of ``ResourceModel`` for the resource that was deleted
        """

        pass

    async def get_all(self) -> AsyncIterable[ResourceModelType]:
        """Helper function to get all items from this resource

        :return: An async iterable with ``ResourceModel`` instances
        """

        async for data in self.get_all_raw():
            doc = self.get_model_instance_from_dict(dict(data))
            yield doc

    def get_all_raw(self) -> AsyncIOMotorCursor:
        return self.mongo_async.find({}).sort("_id")

    async def get_all_batch(self, size=500, max_iterations=10000, lookup=None) -> AsyncIterable[ResourceModelType]:
        """Helper function to get all items from this resource, in batches

        :param size: Number of items to fetch on each iteration
        :param max_iterations: Maximum number of iterations to run, before returning gracefully
        :param lookup: Optional dictionary used to filter items for
        :return: An async iterable with ``ResourceModel`` instances
        """

        last_id: Optional[Union[str, ObjectId]] = None
        if lookup is None:
            lookup = {}
        _lookup = lookup.copy()
        for i in range(max_iterations):
            if last_id is not None:
                _lookup.update({"_id": {"$gt": last_id}})

            cursor = self.mongo_async.find(_lookup).sort("_id").limit(size)
            last_doc = None
            async for data in cursor:
                last_doc = data
                doc = self.get_model_instance_from_dict(data)
                last_id = doc.id
                yield doc
            if last_doc is None:
                break
        else:
            logger.warning(f"Not enough iterations for resource {self.resource_name}")

    @overload
    async def find(
        self, req: SearchRequest
    ) -> ElasticsearchResourceCursorAsync[ResourceModelType] | MongoResourceCursorAsync[ResourceModelType]:
        ...

    @overload
    async def find(
        self,
        req: dict,
        page: int = 1,
        max_results: int = 25,
        sort: SortParam | None = None,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
    ) -> ElasticsearchResourceCursorAsync[ResourceModelType] | MongoResourceCursorAsync[ResourceModelType]:
        ...

    async def find(
        self,
        req: SearchRequest | dict,
        page: int = 1,
        max_results: int = 25,
        sort: SortParam | None = None,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
        # ) -> ResourceCursorAsync[ResourceModelType]:
    ) -> ElasticsearchResourceCursorAsync[ResourceModelType] | MongoResourceCursorAsync[ResourceModelType]:
        """Find items from the resource using Elasticsearch

        :param req: SearchRequest instance, or a lookup dictionary, for the search params to be used
        :param page: The page number to retrieve (defaults to 1)
        :param max_results: The maximum number of results to retrieve per page (defaults to 25)
        :param sort: The sort order to use (defaults to resource default sort, or not sorting applied)
        :param projection: The field projections to be applied
        :param use_mongo: If ``True`` will force use mongo, else will attempt elastic first
        :return: An async iterable with ``ResourceModel`` instances
        :raises SuperdeskApiError.notFoundError: If Elasticsearch is not configured
        """

        search_request = (
            req
            if isinstance(req, SearchRequest)
            else SearchRequest(
                where=req,
                page=page,
                max_results=max_results,
                sort=sort,
                projection=projection,
            )
        )

        if not search_request.projection and self.config.projection:
            search_request.projection = self.config.projection

        if search_request.sort is None:
            search_request.sort = self.config.default_sort

        try:
            if not use_mongo:
                cursor, count = await self.elastic.find(search_request)
                return ElasticsearchResourceCursorAsync(
                    cast(Type[ResourceModelType], self.config.data_class), cursor.hits
                )
        except KeyError:
            pass

        return await self._mongo_find(search_request)

    async def count(self, lookup: dict[str, Any] | None = None, use_mongo: bool = False) -> int:
        """Get the number of items that match the lookup, or all items if lookup is not provided

        Will use Elasticsearch if configured for this resource and ``use_mongo == False``.
        This will not perform a search, but use the item count feature of the underlying data store

        :param lookup: Dictionary to search
        :param use_mongo: Force to use MongoDB instead of Elasticsearch
        :return: The number of items that match the lookup
        """

        try:
            if not use_mongo:
                return await self.elastic.count(lookup)
        except KeyError:
            pass

        return await self.mongo_async.count_documents(lookup or {})

    async def _mongo_find(
        self, req: SearchRequest, versioned: bool = False
    ) -> MongoResourceCursorAsync[ResourceModelType]:
        kwargs: Dict[str, Any] = {}

        if req.max_results:
            kwargs["limit"] = req.max_results
        if req.page > 1:
            kwargs["skip"] = (req.page - 1) * req.max_results

        if req.sort:
            sort = req.sort if isinstance(req.sort, list) else self._convert_req_to_mongo_sort(req.sort)
            if sort:
                kwargs["sort"] = sort

        where = json.loads(req.where or "{}") if isinstance(req.where, str) else req.where or {}
        kwargs["filter"] = where

        projection_include, projection_fields = get_projection_from_request(req)
        if projection_fields:
            kwargs["projection"] = (
                projection_fields if projection_include else {field: False for field in projection_fields}
            )

        cursor = self.mongo_async.find(**kwargs) if not versioned else self.mongo_versioned_async.find(**kwargs)

        return MongoResourceCursorAsync(
            cast(Type[ResourceModelType], self.config.data_class),
            self.mongo_async if not versioned else self.mongo_versioned_async,
            cursor,
            where,
        )

    def _convert_req_to_mongo_sort(self, sort: SortParam | None) -> SortListParam:
        if not sort:
            return []
        elif isinstance(sort, list):
            return sort

        client_sort: SortListParam = []
        try:
            # assume it's mongo syntax, i.e. ?sort=[("name", 1)]
            client_sort = ast.literal_eval(sort)
        except ValueError:
            # It's not mongo so let's see if it's a comma delimited string
            # instead, i.e. "?sort=-age, name"
            for sort_arg in [s.strip() for s in sort.split(",")]:
                if sort_arg[0] == "-":
                    client_sort.append((sort_arg[1:], -1))
                else:
                    client_sort.append((sort_arg, 1))

        return client_sort

    def _convert_dicts_to_model(self, docs: Sequence[ResourceModelType | dict[str, Any]]) -> List[ResourceModelType]:
        return [self.get_model_instance_from_dict(doc) if isinstance(doc, dict) else doc for doc in docs]

    def validate_etag(self, original: ResourceModelType, etag: str | None) -> None:
        """Validate the provided etag against the original

        If the provided ``etag`` argument is ``None``, then validation will not occur

        :param original: Instance of ``ResourceModel`` for the resource to validate etag against
        :param etag: Etag string to validate
        :raises SuperdeskApiError.preconditionFailedError: If the provided etag is invalid
        """

        if not self.config.uses_etag or original.etag is None or etag is None:
            return

        # allow weak etags (we do not support byte-range requests)
        if etag.startswith('W/"'):
            etag = etag.lstrip("W/")
        # remove double quotes from challenge etag format to allow direct
        # string comparison with stored values
        etag = etag.replace('"', "")

        if etag != original.etag:
            raise SuperdeskApiError.preconditionFailedError("Client and server etags don't match")

    def generate_etag(self, value: dict[str, Any], ignore_fields: list[str] | None = None) -> str:
        if ignore_fields is not None:

            def filter_ignore_fields(d, fields):
                # recursive function to remove the fields that they are in d,
                # field is a list of fields to skip or dotted fields to look up
                # to nested keys such as  ["foo", "dict.bar", "dict.joe"]
                for field in fields:
                    key, _, value = field.partition(".")
                    if value and key in d:
                        filter_ignore_fields(d[key], [value])
                    elif field in d:
                        d.pop(field)
                    else:
                        # not required fields can be not present
                        pass

            value_ = deepcopy(value)
            filter_ignore_fields(value_, ignore_fields)
        else:
            value_ = value

        h = sha1()
        json_encoder = SuperdeskJSONEncoder()

        h.update(
            dumps(
                value_,
                sort_keys=True,
                default=json_encoder.default,
                json_options=DEFAULT_JSON_OPTIONS.with_options(
                    uuid_representation=UuidRepresentation.STANDARD,
                ),
            ).encode("utf-8")
        )
        return h.hexdigest()

    async def get_all_item_versions(
        self, item_id: str, max_results: int = 200, page: int = 1
    ) -> tuple[list[dict], int]:
        if not self.config.versioning:
            raise SuperdeskApiError.badRequestError("Resource does not support versioning")

        item: dict | None = await self.mongo_async.find_one({ID_FIELD: item_id})
        if not item:
            raise SuperdeskApiError.notFoundError()

        items: list[dict] = []

        req = SearchRequest(
            where={VERSION_ID_FIELD: item[ID_FIELD]}, max_results=max_results, page=page, sort=[(CURRENT_VERSION, 1)]
        )

        cursor = await self._mongo_find(req, versioned=True)
        versioned_item = await cursor.next_raw()
        while versioned_item is not None:
            self.convert_versioned_item_for_response(item, versioned_item)
            items.append(versioned_item)
            versioned_item = await cursor.next_raw()

        return items, await cursor.count()

    async def get_item_version(self, item: dict, version: int) -> dict:
        if not self.config.versioning:
            raise SuperdeskApiError.badRequestError("Resource does not support versioning")

        versioned_item: dict | None = await self.mongo_versioned_async.find_one(
            {
                VERSION_ID_FIELD: item[ID_FIELD],
                CURRENT_VERSION: version,
            }
        )
        if not versioned_item:
            raise SuperdeskApiError.notFoundError()

        self.convert_versioned_item_for_response(item, versioned_item)
        return versioned_item

    def convert_versioned_item_for_response(self, item: dict, versioned_item: dict):
        versioned_item.update(
            {
                ID_FIELD: versioned_item.pop(VERSION_ID_FIELD),
                LATEST_VERSION: item[CURRENT_VERSION],
            }
        )
        if self.config.ignore_fields_in_versions:
            versioned_item.update({key: item[key] for key in self.config.ignore_fields_in_versions if item.get(key)})

    async def system_update(self, item_id: ObjectId | str, updates: dict[str, Any]) -> None:
        await self.mongo_async.update_one({"_id": item_id}, {"$set": updates})
        try:
            await self.elastic.update(item_id, updates)
        except KeyError:
            pass


class AsyncCacheableService(AsyncResourceService[ResourceModelType]):
    """
    Handles caching for the resource, will invalidate on any changes to the resource.

    Attributes:
        resource_name (str): The name of the resource this service handles.
        cache_lookup (dict): A dictionary to specify custom lookup parameters for caching.
    """

    cache_lookup = {}

    @property
    def cache_key(self) -> str:
        return "cached:{}".format(self.resource_name)

    def get_cache(self) -> Any:
        """
        Retrieve the cached value from Flask's `g` object if available.
        """
        return getattr(g, self.cache_key, None)

    def set_cache(self, value: Any) -> None:
        """
        Set the cached value in Flask's `g` object.
        """
        setattr(g, self.cache_key, value)

    async def get_cached(self) -> List[Dict[str, Any]]:
        """
        Retrieve cached data for the resource. If the cache is empty, fetches data from the database
        and sets it in the cache. The cache is automatically refreshed with a time-to-live (TTL).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the cached data.
        """

        @cache(
            ttl=3600 + random.randrange(1, 300),
            tags=(self.resource_name,),
            key=lambda fn: f"_cache_mixin:{self.resource_name}",
        )
        async def _get_cached_from_db():
            return await _get_from_db()

        async def _get_from_db():
            cursor = await self.search(lookup=self.cache_lookup, use_mongo=True)
            return await cursor.to_list_raw()

        cached_data = self.get_cache()

        if cached_data is None:
            try:
                cached_data = await _get_cached_from_db()
            except RuntimeError:
                # This is sometimes happening, due to lock trying to be released from another thread
                # I think this is mostly happening in tests, but we require a fallback to make
                # sure this will always work
                logger.warning("RuntimeError raised when attempting to get items from cache", exc_info=True)
                cached_data = await _get_from_db()
            self.set_cache(cached_data)

        return cached_data

    async def get_cached_by_id(self, _id: str):
        """
        Retrieve a specific resource by its ID from the cached data. If the resource is not found in
        the cache, fetches it directly from the database.

        Args:
            _id (string): The ID of the resource to retrieve.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the resource if found, otherwise None.
        """
        cached = await self.get_cached()
        for item in cached:
            if item.get("_id") == _id:
                return item
        logger.warning("Cound not find item in cache resource=%s id=%s", self.resource_name, _id)
        return await self.find_by_id(_id)


from .model import ResourceConfig, ResourceModel, get_versioned_model, model_has_versions  # noqa: E402
