from typing import NoReturn

from pydantic_core import ValidationError as PydanticValidationError
from eve.utils import ParsedRequest

from superdesk.core import get_current_async_app
from superdesk.core.types import SearchRequest, SortParam, ItemId
from superdesk.core.resources import AsyncResourceService
from superdesk.core.resources.cursor import DictCursorAsync, MongoResourceCursorAsync
from superdesk.eve_backend import EveBackend
from superdesk.validation import ValidationError as SDValidationError
from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error
from superdesk.errors import SuperdeskApiError


class NonAsyncNotSupported(RuntimeError):
    def __init__(self):
        super().__init__("Non-async functionality is not supported")


class EveToPydanticDataLayer(EveBackend):
    def __init__(self, resource_name: str | None):
        self._resource_name = resource_name

    def get_service(self, endpoint_name: str) -> AsyncResourceService:
        return get_current_async_app().resources.get_resource_service(self._resource_name or endpoint_name)

    async def find_one_async(self, endpoint_name: str, req: ParsedRequest | None, mongo_options: None = None, **lookup):
        if req is None:
            async_req = SearchRequest(
                where=lookup,
                page=1,
                max_results=1,
                use_mongo=True,
            )
        else:
            async_req = SearchRequest(
                args=req.args,
                where=req.where or lookup,
                page=req.page,
                max_results=req.max_results,
                projection=req.projection,
                use_mongo=True,
            )

        item = await self.get_service(endpoint_name).find_one(async_req)
        return item.to_dict() if item else None

    async def find_async(self, endpoint_name: str, where: dict, max_results: int = 0, sort: SortParam | None = None):
        async_req = SearchRequest(
            where=where,
            page=1,
            max_results=max_results,
            use_mongo=True,
            sort=sort,
        )
        return DictCursorAsync(await self.get_service(endpoint_name).find(async_req, use_mongo=True))

    async def search_async(self, endpoint_name: str, source: dict):
        return DictCursorAsync(await self.get_service(endpoint_name).search(source))

    async def search_raw_async(self, endpoint_name: str, source: dict):
        return DictCursorAsync(await self.get_service(endpoint_name).search(source))

    async def get_async(self, endpoint_name: str, req: ParsedRequest, lookup: dict | None, **kwargs):
        async_req = SearchRequest(
            args=req.args,
            where=req.where or lookup,
            page=req.page,
            max_results=req.max_results,
            projection=req.projection,
        )

        return DictCursorAsync(await self.get_service(endpoint_name).find(async_req))

    async def get_from_mongo_async(
        self, endpoint_name: str, req: ParsedRequest, lookup: dict | None, perform_count: bool = False
    ):
        async_req = SearchRequest(
            args=req.args,
            where=req.where or lookup,
            page=req.page,
            max_results=req.max_results,
            projection=req.projection,
        )

        cursor = await self.get_service(endpoint_name).find(async_req, use_mongo=True)
        if not isinstance(cursor, MongoResourceCursorAsync):
            raise SuperdeskApiError.internalError("Expected a MongoDB cursor")

        return cursor.cursor

    async def find_and_modify_async(self, endpoint_name: str, **kwargs) -> dict | None:
        eve_mongo_backend = self._backend(endpoint_name, use_async=True)

        query = kwargs.get("query") or kwargs.get("filter")
        if query:
            kwargs["filter"] = eve_mongo_backend._mongotize(query, endpoint_name)
            kwargs.pop("query", None)

        return await self.get_service(endpoint_name).mongo_async.find_one_and_update(**kwargs)

    async def create_async(self, endpoint_name: str, docs: list[dict], skip_signals: bool = False, **kwargs):
        try:
            new_items = await self.get_service(endpoint_name).create(docs, skip_signals=skip_signals)
        except PydanticValidationError as error:
            # re-raise the exception as a Cerberus/Eve type error
            errors = get_field_errors_from_pydantic_validation_error(error)
            raise SDValidationError(errors)

        new_items_map = {item.id: item for item in new_items}

        # Make sure to update the provided `docs` variable, as that's what's returned to the client
        # when using Eve API layer
        for doc in docs:
            new_item = new_items_map.get(doc["_id"])
            if new_item:
                doc.update(new_item.to_dict())

        # And add any generated items to the `docs` variable (such as recurring events)
        provided_doc_ids = [str(doc["_id"]) for doc in docs]
        for item in new_items:
            if str(item.id) not in provided_doc_ids:
                docs.append(item.to_dict())

        return [item.id for item in new_items]

    async def create_in_mongo_async(self, endpoint_name: str, docs: list[dict], **kwargs) -> list[ItemId]:
        service = self.get_service(endpoint_name)
        for doc in docs:
            self.set_default_dates(doc)
            if not doc.get("_etag"):
                doc["_etag"] = service.generate_etag(doc, service.config.etag_ignore_fields)

        return (await service.mongo_async.insert_many(docs, ordered=True)).inserted_ids

    async def create_in_search_async(self, endpoint_name: str, docs: list[dict], **kwargs) -> list[ItemId]:
        return await self.get_service(endpoint_name).elastic.insert(docs)

    async def update_async(
        self, endpoint_name: str, item_id: ItemId, updates: dict, original: dict, skip_signals: bool = False
    ):
        try:
            updated_item = await self.get_service(endpoint_name).update(item_id, updates, skip_signals=skip_signals)
        except PydanticValidationError as error:
            # re-raise the exception as a Cerberus/Eve type error
            errors = get_field_errors_from_pydantic_validation_error(error)
            raise SDValidationError(errors)

        updated_dict = updated_item.to_dict()
        for key in updated_dict.keys():
            # TODO-UNIFIED: Only assign fields to `updates` that have changed
            updates[key] = updated_dict[key]

        return updates

    async def system_update_async(
        self,
        endpoint_name: str,
        item_id: ItemId,
        updates: dict,
        original: dict,
        change_request: bool = False,
        push_notification: bool = True,
    ):
        return await self.get_service(endpoint_name).system_update(item_id, updates)

    async def replace_async(self, endpoint_name: str, item_id: ItemId, document: dict, original: dict):
        service = self.get_service(endpoint_name)
        original_model = await service.find_by_id(item_id)
        if not original_model:
            raise SuperdeskApiError.notFoundError()

        await service.update_in_dbs(item_id, original_model, document, document, replace=True)

    async def update_in_mongo_async(self, endpoint_name: str, item_id: ItemId, updates: dict, original: dict):
        service = self.get_service(endpoint_name)
        original_model = await service.find_by_id(item_id)
        if not original_model:
            raise SuperdeskApiError.notFoundError()

        await service.update_in_dbs(item_id, original_model, updates, updates, replace=False, update_elastic=False)

    async def replace_in_mongo_async(self, endpoint_name: str, item_id: ItemId, document: dict, original: dict):
        service = self.get_service(endpoint_name)
        original_model = await service.find_by_id(item_id)
        if not original_model:
            raise SuperdeskApiError.notFoundError()

        await service.update_in_dbs(item_id, original_model, document, document, replace=True, update_elastic=False)

    async def replace_in_search_async(self, endpoint_name: str, item_id: ItemId, document: dict, original: dict):
        service = self.get_service(endpoint_name)
        original_model = await service.find_by_id(item_id)
        if not original_model:
            raise SuperdeskApiError.notFoundError()

        await service.update_in_dbs(item_id, original_model, document, document, replace=True, update_mongo=False)

    async def delete_async(self, endpoint_name: str, lookup: dict) -> list[ItemId]:
        return await self.get_service(endpoint_name).delete_many(lookup)

    async def delete_docs_async(self, endpoint_name: str, docs: list[dict]):
        return await self.get_service(endpoint_name).delete_many({"_id": {"$in": [doc["_id"] for doc in docs]}})

    async def delete_ids_from_mongo_async(self, endpoint_name: str, ids: list[ItemId]):
        await self.delete_from_mongo_async(endpoint_name, {"_id": {"$in": ids}})

    async def delete_from_mongo_async(self, endpoint_name: str, lookup: dict):
        await self.get_service(endpoint_name).delete_many(lookup)

    async def remove_from_search_async(self, endpoint_name: str, doc: dict):
        await self.get_service(endpoint_name).elastic.remove(doc["_id"])

    async def count_async(self, endpoint_name: str, lookup: dict | None = None) -> int:
        return await self.get_service(endpoint_name).count(lookup, use_mongo=True)

    # The following sync methods are not supported
    def find_one(self, endpoint_name: str, req: ParsedRequest, **lookup) -> NoReturn:
        raise NonAsyncNotSupported()

    def find(self, endpoint_name: str, where: dict, max_results: int = 0, sort: SortParam | None = None) -> NoReturn:
        raise NonAsyncNotSupported()

    def search(self, endpoint_name: str, source: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def search_raw(self, endpoint_name: str, source: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def get(self, endpoint_name: str, req: ParsedRequest, lookup: dict | None, **kwargs) -> NoReturn:
        raise NonAsyncNotSupported()

    def get_from_mongo(
        self, endpoint_name: str, req: ParsedRequest, lookup: dict | None, perform_count: bool = False
    ) -> NoReturn:
        raise NonAsyncNotSupported()

    def find_and_modify(self, endpoint_name: str, **kwargs) -> NoReturn:
        raise NonAsyncNotSupported()

    def create(self, endpoint_name: str, docs: list[dict], **kwargs) -> NoReturn:
        raise NonAsyncNotSupported()

    def create_in_mongo(self, endpoint_name: str, docs: list[dict], **kwargs) -> NoReturn:
        raise NonAsyncNotSupported()

    def create_in_search(self, endpoint_name: str, docs: list[dict], **kwargs) -> NoReturn:
        raise NonAsyncNotSupported()

    def update(self, endpoint_name: str, item_id: ItemId, updates: dict, original: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def system_update(
        self,
        endpoint_name: str,
        item_id: ItemId,
        updates: dict,
        original: dict,
        change_request: bool = False,
        push_notification: bool = True,
    ) -> NoReturn:
        raise NonAsyncNotSupported()

    def replace(self, endpoint_name: str, item_id: ItemId, document: dict, original: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def update_in_mongo(self, endpoint_name: str, item_id: ItemId, updates: dict, original: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def replace_in_mongo(self, endpoint_name: str, item_id: ItemId, document: dict, original: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def replace_in_search(self, endpoint_name: str, item_id: ItemId, document: dict, original: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def delete(self, endpoint_name: str, lookup: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def delete_docs(self, endpoint_name: str, docs: list[dict]) -> NoReturn:
        raise NonAsyncNotSupported()

    def delete_ids_from_mongo(self, endpoint_name: str, ids: list[ItemId]) -> NoReturn:
        raise NonAsyncNotSupported()

    def delete_from_mongo(self, endpoint_name: str, lookup: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def remove_from_search(self, endpoint_name: str, doc: dict) -> NoReturn:
        raise NonAsyncNotSupported()

    def count(self, resource: str, lookup: dict | None = None) -> NoReturn:
        raise NonAsyncNotSupported()
