import logging

import pymongo
from eve.utils import ParsedRequest
from eve.methods.common import resolve_document_etag

from superdesk.services import BaseService
from superdesk.resource_fields import ETAG
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError


logger = logging.getLogger(__name__)


class AsyncBaseService(BaseService):
    is_async = True

    async def on_create_async(self, docs):
        pass

    async def on_created_async(self, docs):
        pass

    async def on_update_async(self, updates, original):
        pass

    async def on_updated_async(self, updates, original):
        pass

    async def on_replace_async(self, document, original):
        pass

    async def on_replaced_async(self, document, original):
        pass

    async def on_delete_async(self, doc):
        pass

    async def on_deleted_async(self, doc):
        pass

    async def on_fetched_async(self, doc):
        pass

    async def on_fetched_item_async(self, doc):
        pass

    async def create_async(self, docs, **kwargs):
        ids = await self.backend.create_async(self.datasource, docs, **kwargs)
        return ids

    async def update_async(self, id, updates, original):
        return await self.backend.update_async(self.datasource, id, updates, original)

    async def system_update_async(self, id, updates, original, **kwargs):
        return await self.backend.system_update_async(self.datasource, id, updates, original, **kwargs)

    async def replace_async(self, id, document, original):
        return await self.backend.replace_async(self.datasource, id, document, original)

    async def delete_async(self, lookup):
        return await self.backend.delete_async(self.datasource, lookup)

    async def delete_ids_from_mongo_async(self, ids):
        return await self.backend.delete_ids_from_mongo_async(self.datasource, ids)

    async def delete_from_mongo_async(self, lookup: dict):
        """Delete items from mongo only

        .. versionadded:: 2.4.0

        .. warning:: ``on_delete`` and ``on_deleted`` is **NOT** called with this action

        :param dict lookup: User mongo query syntax
        :raises SuperdeskApiError.forbiddenError if search is enabled for this resource
        """

        await self.backend.delete_from_mongo_async(self.datasource, lookup)

    async def delete_docs_async(self, docs):
        for doc in docs:
            self.on_delete(doc)
            await self.on_delete_async(doc)
        res = await self.backend.delete_docs_async(self.datasource, docs)
        for doc in docs:
            self.on_deleted(doc)
            await self.on_deleted_async(doc)
        return res

    async def find_one_async(self, req, **lookup):
        return await self.backend.find_one_async(self.datasource, req=req, **lookup)

    async def find_async(self, where, **kwargs):
        """Find items in service collection using mongo query.

        :param dict where:
        """
        return await self.backend.find_async(self.datasource, where, **kwargs)

    async def get_async(self, req, lookup):
        if req is None:
            req = ParsedRequest()
        return await self.backend.get_async(self.datasource, req=req, lookup=lookup)

    async def get_from_mongo_async(self, req, lookup, projection=None):
        if req is None:
            req = ParsedRequest()
        if not req.projection and projection:
            from superdesk.core import json

            req.projection = json.dumps(projection)
        return await self.backend.get_from_mongo_async(self.datasource, req=req, lookup=lookup)

    async def get_all_async(self):
        return await self.get_from_mongo(None, {}).sort("_id")

    async def find_and_modify_async(self, query, update, **kwargs):
        return await self.backend.find_and_modify_async(self.datasource, filter=query, update=update, **kwargs)

    async def get_all_batch_async(self, size=500, max_iterations=10000, lookup=None):
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

            # TODO-ASYNC: Fix this - use async for cursor iteration
            items = list(await self.get_from_mongo_async(req=None, lookup=_lookup).sort("_id").limit(size))
            if not len(items):
                break
            for item in items:
                yield item
                last_id = item["_id"]
        else:
            logger.warning("Not enough iterations for resource %s", self.datasource)

    async def post_async(self, docs, **kwargs):
        for doc in docs:
            self._resolve_defaults(doc)
        await self.on_create_async(docs)
        self.on_create(docs)
        ids = await self.create_async(docs, **kwargs)
        await self.on_created_async(docs)
        self.on_created(docs)
        return ids

    async def patch_async(self, id, updates):
        from superdesk.core import get_app_config

        original = await self.find_one_async(req=None, _id=id)
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

    async def put_async(self, id, document):
        self._resolve_defaults(document)
        original = await self.find_one_async(req=None, _id=id)
        await self.on_replace_async(document, original)
        self.on_replace(document, original)
        resolve_document_etag(document, self.datasource)
        res = await self.replace_async(id, document, original)
        await self.on_replaced_async(document, original)
        self.on_replaced(document, original)
        return res

    async def delete_action_async(self, lookup=None):
        if lookup is None:
            lookup = {}
            docs = []
        else:
            # TODO-ASYNC: Fix this
            docs = list(doc for doc in self.get_from_mongo_async(None, lookup).sort("_id", pymongo.ASCENDING))
        if not docs:
            return self.delete_async(lookup)
        return self.delete_docs_async(docs)

    async def search_async(self, source):
        """Search using search backend.

        :param source: query source param
        """
        # TODO-ASYNC: Convert this to use elastic async
        return self.backend.search(self.datasource, source)

    async def remove_from_search_async(self, item):
        """Remove item from search.

        :param dict item: item
        """

        # TODO-ASYNC: Convert this to use elastic async
        return self.backend.remove_from_search(self.datasource, item)

    async def update_data_from_json_async(self, items):
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
