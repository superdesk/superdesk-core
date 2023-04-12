# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import pymongo
import logging

from typing import Dict, Any, List, Optional, Union
from flask import current_app as app, json, g
from eve.utils import ParsedRequest, config
from eve.methods.common import resolve_document_etag
from superdesk.errors import SuperdeskApiError
from superdesk.utc import utcnow
from superdesk.cache import cache


logger = logging.getLogger(__name__)


class BaseService:
    """
    Base service for all endpoints, defines the basic implementation for CRUD datalayer functionality.
    """

    datasource: Union[str, None]

    def __init__(self, datasource: Optional[str] = None, backend=None):
        self.backend = backend
        self.datasource = datasource

    def init(self, datasource: str, backend=None):
        self.datasource = datasource
        self.backend = backend

    def on_create(self, docs):
        pass

    def on_created(self, docs):
        pass

    def on_update(self, updates, original):
        pass

    def on_updated(self, updates, original):
        pass

    def on_replace(self, document, original):
        pass

    def on_replaced(self, document, original):
        pass

    def on_delete(self, doc):
        pass

    def on_deleted(self, doc):
        pass

    def on_fetched(self, doc):
        pass

    def on_fetched_item(self, doc):
        pass

    def create(self, docs, **kwargs):
        ids = self.backend.create(self.datasource, docs, **kwargs)
        return ids

    def update(self, id, updates, original):
        return self.backend.update(self.datasource, id, updates, original)

    def system_update(self, id, updates, original, **kwargs):
        return self.backend.system_update(self.datasource, id, updates, original, **kwargs)

    def replace(self, id, document, original):
        res = self.backend.replace(self.datasource, id, document, original)
        return res

    def delete(self, lookup):
        res = self.backend.delete(self.datasource, lookup)
        return res

    def delete_ids_from_mongo(self, ids):
        res = self.backend.delete_ids_from_mongo(self.datasource, ids)
        return res

    def delete_from_mongo(self, lookup: Dict[str, Any]):
        """Delete items from mongo only

        .. versionadded:: 2.4.0

        .. warning:: ``on_delete`` and ``on_deleted`` is **NOT** called with this action

        :param dict lookup: User mongo query syntax
        :raises SuperdeskApiError.forbiddenError if search is enabled for this resource
        """

        self.backend.delete_from_mongo(self.datasource, lookup)

    def delete_docs(self, docs):
        return self.backend.delete_docs(self.datasource, docs)

    def find_one(self, req, **lookup):
        res = self.backend.find_one(self.datasource, req=req, **lookup)
        return res

    def find(self, where, **kwargs):
        """Find items in service collection using mongo query.

        :param dict where:
        """
        return self.backend.find(self.datasource, where, **kwargs)

    def get(self, req, lookup):
        if req is None:
            req = ParsedRequest()
        return self.backend.get(self.datasource, req=req, lookup=lookup)

    def get_from_mongo(self, req, lookup, projection=None):
        if req is None:
            req = ParsedRequest()
        if not req.projection and projection:
            req.projection = json.dumps(projection)
        return self.backend.get_from_mongo(self.datasource, req=req, lookup=lookup)

    def get_all(self):
        return self.get_from_mongo(None, {}).sort("_id")

    def find_and_modify(self, query, update, **kwargs):
        res = self.backend.find_and_modify(self.datasource, query=query, update=update, **kwargs)
        return res

    def get_all_batch(self, size=500, max_iterations=10000):
        """Gets all items using multiple queries.

        When processing big collection and doing something time consuming you might get
        a mongo cursor timeout, this should avoid it fetching `size` items in memory
        and closing the cursor in between.
        """
        last_id = None
        for i in range(max_iterations):
            if last_id is not None:
                lookup = {"_id": {"$gt": last_id}}
            else:
                lookup = {}
            items = list(self.get_from_mongo(req=None, lookup=lookup).sort("_id").limit(size))
            if not len(items):
                break
            for item in items:
                yield item
                last_id = item["_id"]
        else:
            logger.warning("Not enough iterations for resource %s", self.datasource)

    def _validator(self, skip_validation=False):
        resource_def = app.config["DOMAIN"][self.datasource]
        schema = resource_def["schema"]
        return (
            None
            if skip_validation
            else app.validator(schema, resource=self.datasource, allow_unknown=resource_def["allow_unknown"])
        )

    def _resolve_defaults(self, doc):
        validator = self._validator()
        if validator:
            normalized = validator.normalized(doc, always_return_document=True)
            doc.update(normalized)
        return doc

    def post(self, docs, **kwargs):
        for doc in docs:
            self._resolve_defaults(doc)
        self.on_create(docs)
        ids = self.create(docs, **kwargs)
        self.on_created(docs)
        return ids

    def patch(self, id, updates):
        original = self.find_one(req=None, _id=id)
        updated = original.copy()
        self.on_update(updates, original)
        updated.update(updates)
        if config.IF_MATCH:
            resolve_document_etag(updated, self.datasource)
            updates[config.ETAG] = updated[config.ETAG]
        res = self.update(id, updates, original)
        self.on_updated(updates, original)
        return res

    def put(self, id, document):
        self._resolve_defaults(document)
        original = self.find_one(req=None, _id=id)
        self.on_replace(document, original)
        resolve_document_etag(document, self.datasource)
        res = self.replace(id, document, original)
        self.on_replaced(document, original)
        return res

    def delete_action(self, lookup=None):
        if lookup is None:
            lookup = {}
            docs = []
        else:
            docs = list(doc for doc in self.get_from_mongo(None, lookup).sort("_id", pymongo.ASCENDING))
        for doc in docs:
            self.on_delete(doc)
        res = self.delete(lookup)
        for doc in docs:
            self.on_deleted(doc)
        return res

    def is_authorized(self, **kwargs):
        """Subclass should override if the resource handled by the service has intrinsic privileges.

        :param kwargs: should have properties which help in authorizing the request
        :return: ``False`` if unauthorized and True if authorized
        """
        return True

    def search(self, source):
        """Search using search backend.

        :param source: query source param
        """
        return self.backend.search(self.datasource, source)

    def remove_from_search(self, item):
        """Remove item from search.

        :param dict item: item
        """
        return self.backend.remove_from_search(self.datasource, item)

    def update_data_from_json(self, items):
        success = []
        for item in items:
            try:
                orig = self.find_one(req=None, _id=item["_id"])
                # update _created and _updated key if keys provided in json
                if item.get("_created"):
                    item["_created"] = orig["_created"] if orig else utcnow()
                if item.get("_updated"):
                    item["_updated"] = utcnow()

                res = self.post([item]) if not orig else self.patch(orig["_id"], item)
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


class Service(BaseService):
    pass


class CacheableService(BaseService):
    """Handles caching for the resource, will invalidate on any changes to the resource."""

    datasource: str
    cache_lookup = {}

    @property
    def cache_key(self) -> str:
        return "cached:{}".format(self.datasource)

    def get_cached(self) -> List[Dict[str, Any]]:
        @cache(ttl=3600, tags=(self.datasource,), key=lambda fn: f"_cache_mixin:{self.datasource}")
        def _get_cached_from_db():
            return list(self.get_from_mongo(req=None, lookup=self.cache_lookup))

        if not hasattr(g, self.cache_key):
            setattr(g, self.cache_key, _get_cached_from_db())

        return getattr(g, self.cache_key)

    def get_cached_by_id(self, _id):
        cached = self.get_cached()
        for item in cached:
            if item.get("_id") == _id:
                return item
        logger.warning("Cound not find item in cache resource=%s id=%s", self.datasource, _id)
        return self.find_one(req=None, _id=_id)
