from typing import AsyncIterator, cast
import logging

import pymongo
from eve.utils import ParsedRequest
from eve.methods.common import resolve_document_etag
from quart_babel import gettext

from superdesk.core.types import ItemId
from superdesk.services import BaseService, CacheableService
from superdesk.resource_fields import ETAG
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError

from .cursors import AsyncEveCursor, MongoAsyncEveCursor, ElasticAsyncEveCursor


logger = logging.getLogger(__name__)


class AsyncBaseService(BaseService):
    is_async = True

    async def on_create_async(self, docs: list[dict]) -> None:
        pass

    async def on_created_async(self, docs: list[dict]) -> None:
        pass

    async def on_update_async(self, updates: dict, original: dict) -> None:
        pass

    async def on_updated_async(self, updates: dict, original: dict) -> None:
        pass

    async def on_replace_async(self, document: dict, original: dict) -> None:
        pass

    async def on_replaced_async(self, document: dict, original: dict) -> None:
        pass

    async def on_delete_async(self, doc: dict) -> None:
        pass

    async def on_deleted_async(self, doc: dict) -> None:
        pass

    async def on_fetched_async(self, doc: dict) -> None:
        pass

    async def on_fetched_item_async(self, doc: dict) -> None:
        pass

    async def create_async(self, docs: list[dict], **kwargs) -> list[ItemId]:
        ids = await self.backend.create_async(self.datasource, docs, **kwargs)
        return ids

    async def update_async(self, id: ItemId, updates: dict, original: dict) -> dict:
        return await self.backend.update_async(self.datasource, id, updates, original)

    async def system_update_async(self, id: ItemId, updates: dict, original: dict, **kwargs) -> dict:
        return await self.backend.system_update_async(self.datasource, id, updates, original, **kwargs)

    async def replace_async(self, id: ItemId, document: dict, original: dict) -> None:
        return await self.backend.replace_async(self.datasource, id, document, original)

    async def delete_async(self, lookup: dict) -> list[ItemId]:
        return await self.backend.delete_async(self.datasource, lookup)

    async def delete_ids_from_mongo_async(self, ids: list[ItemId]) -> list[ItemId]:
        return await self.backend.delete_ids_from_mongo_async(self.datasource, ids)

    async def delete_from_mongo_async(self, lookup: dict) -> None:
        """Delete items from mongo only

        .. versionadded:: 2.4.0

        .. warning:: ``on_delete`` and ``on_deleted`` is **NOT** called with this action

        :param dict lookup: User mongo query syntax
        :raises SuperdeskApiError.forbiddenError if search is enabled for this resource
        """

        await self.backend.delete_from_mongo_async(self.datasource, lookup)

    async def delete_docs_async(self, docs: list[dict]) -> list[ItemId]:
        for doc in docs:
            self.on_delete(doc)
            await self.on_delete_async(doc)
        res = await self.backend.delete_docs_async(self.datasource, docs)
        for doc in docs:
            self.on_deleted(doc)
            await self.on_deleted_async(doc)
        return res

    async def find_one_async(self, req: ParsedRequest | None, **lookup) -> dict | None:
        return await self.backend.find_one_async(self.datasource, req=req, **lookup)

    async def find_async(self, where, **kwargs) -> MongoAsyncEveCursor:
        """Find items in service collection using mongo query.

        :param dict where:
        """
        return await self.backend.find_async(self.datasource, where, **kwargs)

    async def get_async(self, req: ParsedRequest | None, lookup: dict | None) -> AsyncEveCursor:
        if req is None:
            req = ParsedRequest()
        return await self.backend.get_async(self.datasource, req=req, lookup=lookup)

    async def get_from_mongo_async(
        self, req: ParsedRequest | None, lookup: dict | None, projection: dict | None = None
    ) -> MongoAsyncEveCursor:
        if req is None:
            req = ParsedRequest()
        if not req.projection and projection:
            from superdesk.core import json

            req.projection = json.dumps(projection)
        return await self.backend.get_from_mongo_async(self.datasource, req=req, lookup=lookup)

    async def get_all_async(self) -> MongoAsyncEveCursor:
        return (await self.get_from_mongo_async(None, {})).sort("_id")

    async def find_and_modify_async(self, query: dict, update: dict, **kwargs) -> dict:
        return await self.backend.find_and_modify_async(self.datasource, filter=query, update=update, **kwargs)

    async def get_all_batch_async(
        self, size: int = 500, max_iterations: int = 10000, lookup: dict | None = None
    ) -> AsyncIterator[dict]:
        """Gets all items using multiple queries.

        When processing big collection and doing something time consuming you might get
        a mongo cursor timeout, this should avoid it fetching `size` items in memory
        and closing the cursor in between.
        """

        last_id = None
        if lookup is None:
            lookup = {}
        _lookup = lookup.copy()
        for i in range(max_iterations):
            if last_id is not None:
                _lookup = {"_id": {"$gt": last_id}}

            cursor = (await self.get_from_mongo_async(req=None, lookup=_lookup)).sort("_id").limit(size)
            # As the consumer might be doing something time-consuming, we consume the entire cursor now
            # to get all items, otherwise there may be a cursor timeout
            items = [item async for item in cursor]
            if not len(items):
                break
            for item in items:
                yield cast(dict, item)
                last_id = item["_id"]
        else:
            logger.warning("Not enough iterations for resource %s", self.datasource)

    async def post_async(self, docs: list[dict], **kwargs) -> list[ItemId]:
        for doc in docs:
            self._resolve_defaults(doc)
        await self.on_create_async(docs)
        self.on_create(docs)
        ids = await self.create_async(docs, **kwargs)
        await self.on_created_async(docs)
        self.on_created(docs)
        return ids

    async def patch_async(self, id: ItemId, updates: dict) -> dict:
        from superdesk.core import get_app_config

        original = await self.find_one_async(req=None, _id=id)
        if original is None:
            raise SuperdeskApiError.notFoundError(gettext(f"Item with id {id} not found"))

        updated = original.copy()
        await self.on_update_async(updates, original)
        self.on_update(updates, original)
        updated.update(updates)
        if get_app_config("IF_MATCH"):
            resolve_document_etag(updated, self.datasource)
            updates[ETAG] = updated[ETAG]
        res = await self.update_async(id, updates, original)
        await self.on_updated_async(updates, original)
        self.on_updated(updates, original)
        return res

    async def put_async(self, id: ItemId, document: dict) -> None:
        self._resolve_defaults(document)
        original = await self.find_one_async(req=None, _id=id)
        if original is None:
            raise SuperdeskApiError.notFoundError(gettext(f"Item with id {id} not found"))

        await self.on_replace_async(document, original)
        self.on_replace(document, original)
        resolve_document_etag(document, self.datasource)
        await self.replace_async(id, document, original)
        await self.on_replaced_async(document, original)
        self.on_replaced(document, original)

    async def delete_action_async(self, lookup: dict | None = None) -> list[ItemId]:
        if lookup is None:
            lookup = {}
            docs = []
        else:
            cursor = (await self.get_from_mongo_async(None, lookup)).sort("_id", pymongo.ASCENDING)
            docs = [dict(doc) async for doc in cursor]
        if not docs:
            return await self.delete_async(lookup)
        return await self.delete_docs_async(docs)

    async def search_async(self, source: dict) -> ElasticAsyncEveCursor | None:
        """Search using search backend.

        :param source: query source param
        """
        return await self.backend.search_async(self.datasource, source)

    async def remove_from_search_async(self, item: dict) -> dict:
        """Remove item from search.

        :param dict item: item
        """

        return await self.backend.remove_from_search_async(self.datasource, item)

    async def update_data_from_json_async(self, items: dict) -> dict:
        success = []
        for item in items:
            try:
                orig = await self.find_one_async(req=None, _id=item["_id"])
                # update _created and _updated key if keys provided in json
                if item.get("_created"):
                    item["_created"] = orig["_created"] if orig else utcnow()
                if item.get("_updated"):
                    item["_updated"] = utcnow()

                res = await (self.post_async([item]) if not orig else self.patch_async(orig["_id"], item))
                if res:
                    success.append(res)
            except Exception as ex:
                raise SuperdeskApiError.badRequestError("Uploaded file is invalid, Error occured:{}.".format(str(ex)))

        if success:
            return {
                "_status": "SUCCESS",
                "_success": {"code": 200, "_message": "{} uploaded successfully.".format(self.datasource)},
                "items": success,
            }

        return {
            "_status": "ERR",
            "_error": {"code": 400, "_message": "Unable to update {}.".format(self.datasource)},
            "items": items,
        }


class CachableAsyncBaseService(AsyncBaseService, CacheableService):
    pass
