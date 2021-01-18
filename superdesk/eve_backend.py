# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import eve.io.base

import json as std_json
from pymongo.cursor import Cursor as MongoCursor
from pymongo.collation import Collation
from flask import current_app as app, json
from eve.utils import document_etag, config, ParsedRequest
from eve.io.mongo import MongoJSONEncoder
from superdesk.utc import utcnow
from superdesk.logging import logger, item_msg
from eve.methods.common import resolve_document_etag
from elasticsearch.exceptions import RequestError, NotFoundError
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification


SYSTEM_KEYS = set([
    '_etag',
    '_updated',
    '_created',
])


def get_key(key, parent=None):
    return '.'.join(filter(None, [parent, key]))


def get_diff_keys(updates, original=None, parent=None):
    if original is None:
        original = {}
    if original and parent:
        keys = set([
            get_key(key, parent) for key in set(original.keys()) - set(updates.keys())
        ])
    else:
        keys = set()
    for key, val in updates.items():
        if key not in original or original[key] != val:
            keys.add(get_key(key, parent))
            if not parent and val and isinstance(val, dict):
                keys.update(get_diff_keys(val, original.get(key), key).keys())
    return {key: 1 for key in keys if key not in SYSTEM_KEYS}


class EveBackend():
    """Superdesk data backend, handles mongodb/elastic data storage."""

    def find_one(self, endpoint_name, req, **lookup):
        """Find single item.

        :param endpoint_name: resource name
        :param req: parsed request
        :param lookup: additional filter
        """
        backend = self._backend(endpoint_name)
        item = backend.find_one(endpoint_name, req=req, **lookup)
        search_backend = self._lookup_backend(endpoint_name, fallback=True)
        if search_backend:
            # set the parent for the parent child in elastic search
            self._set_parent(endpoint_name, item, lookup)
            item_search = search_backend.find_one(endpoint_name, req=req, **lookup)
            if item is None and item_search:
                item = item_search
                logger.warn(item_msg('item is only in elastic', item))
            elif item_search is None and item:
                logger.warn(item_msg('item is only in mongo', item))
                try:
                    logger.info(item_msg('trying to add item to elastic', item))
                    search_backend.insert(endpoint_name, [item])
                except RequestError as e:
                    logger.error(item_msg('failed to add item into elastic error={}'.format(str(e)), item))
        return item

    def find(self, endpoint_name, where, max_results=0, sort=None):
        """Find items for given endpoint using mongo query in python dict object.

        It handles request creation here so no need to do this in service.

        :param string endpoint_name
        :param dict where
        :param int max_results
        """
        req = ParsedRequest()
        req.where = MongoJSONEncoder().encode(where)
        req.max_results = max_results
        if sort is not None:
            req.sort = sort
        return self.get_from_mongo(endpoint_name, req, None)

    def search(self, endpoint_name, source):
        """Search for items using search backend

        :param string endpoint_name
        :param dict source
        """
        req = ParsedRequest()
        req.args = {'source': json.dumps(source)}
        search_backend = self._lookup_backend(endpoint_name)
        if search_backend:
            return search_backend.find(endpoint_name, req, {})
        else:
            logger.warn('there is no search backend for %s' % endpoint_name)

    def get(self, endpoint_name, req, lookup, **kwargs):
        """Get list of items.

        :param endpoint_name: resource name
        :param req: parsed request
        :param lookup: additional filter
        """
        backend = self._lookup_backend(endpoint_name, fallback=True)
        is_mongo = self._backend(endpoint_name) == backend

        if is_mongo:
            cursor, count = backend.find(endpoint_name, req, lookup)
        else:
            cursor = backend.find(endpoint_name, req, lookup)
            count = cursor.count()

        if req.if_modified_since and count:
            # fetch all items, not just updated
            req.if_modified_since = None
            if is_mongo:
                cursor, count = backend.find(endpoint_name, req, lookup)
            else:
                cursor = backend.find(endpoint_name, req, lookup)
                count = cursor.count()

        self._cursor_hook(cursor=cursor, req=req)
        return cursor

    def get_from_mongo(self, endpoint_name, req, lookup):
        """Get list of items from mongo.

        No matter if there is elastic configured, this will use mongo.

        :param endpoint_name: resource name
        :param req: parsed request
        :param lookup: additional filter
        """
        req.if_modified_since = None
        backend = self._backend(endpoint_name)
        cursor, _ = backend.find(endpoint_name, req, lookup)
        self._cursor_hook(cursor=cursor, req=req)
        return cursor

    def find_and_modify(self, endpoint_name, **kwargs):
        """Find and modify in mongo.

        :param endpoint_name: resource name
        :param kwargs: kwargs for pymongo ``find_and_modify``
        """
        backend = self._backend(endpoint_name)

        if kwargs.get('query'):
            kwargs['query'] = backend._mongotize(kwargs['query'], endpoint_name)

        return backend.driver.db[endpoint_name].find_and_modify(**kwargs)

    def create(self, endpoint_name, docs, **kwargs):
        """Insert documents into given collection.

        :param endpoint_name: api resource name
        :param docs: list of docs to be inserted
        """
        for doc in docs:
            doc.pop('_type', None)
        ids = self.create_in_mongo(endpoint_name, docs, **kwargs)
        self.create_in_search(endpoint_name, docs, **kwargs)
        return ids

    def create_in_mongo(self, endpoint_name, docs, **kwargs):
        """Create items in mongo.

        :param endpoint_name: resource name
        :param docs: list of docs to create
        """
        for doc in docs:
            self.set_default_dates(doc)
            if not doc.get(config.ETAG):
                doc[config.ETAG] = document_etag(doc)

        backend = self._backend(endpoint_name)
        ids = backend.insert(endpoint_name, docs)
        return ids

    def create_in_search(self, endpoint_name, docs, **kwargs):
        """Create items in elastic.

        :param endpoint_name: resource name
        :param docs: list of docs
        """
        search_backend = self._lookup_backend(endpoint_name)
        if search_backend:
            search_backend.insert(endpoint_name, docs, **kwargs)

    def update(self, endpoint_name, id, updates, original):
        """Update document with given id.

        :param endpoint_name: api resource name
        :param id: document id
        :param updates: changes made to document
        :param original: original document
        """
        # change etag on update so following request will refetch it
        updates.setdefault(config.LAST_UPDATED, utcnow())
        if config.ETAG not in updates:
            updated = original.copy()
            updated.update(updates)
            resolve_document_etag(updated, endpoint_name)
            if config.IF_MATCH:
                updates[config.ETAG] = updated[config.ETAG]
        return self._change_request(endpoint_name, id, updates, original)

    def system_update(self, endpoint_name, id, updates, original):
        """Only update what is provided, without affecting etag.

        This is useful when you want to make some changes without affecting users.

        :param endpoint_name: api resource name
        :param id: document id
        :param updates: changes made to document
        :param original: original document
        """
        updates.setdefault(config.LAST_UPDATED, utcnow())
        updated = original.copy()
        updated.pop(config.ETAG, None)  # make sure we update
        return self._change_request(endpoint_name, id, updates, updated)

    def _change_request(self, endpoint_name, id, updates, original):
        backend = self._backend(endpoint_name)
        search_backend = self._lookup_backend(endpoint_name)

        try:
            backend.update(endpoint_name, id, updates, original)
            push_notification('resource:updated', _id=str(id),
                              resource=endpoint_name, fields=get_diff_keys(updates, original))
        except eve.io.base.DataLayer.OriginalChangedError:
            if not backend.find_one(endpoint_name, req=None, _id=id) and search_backend:
                # item is in elastic, not in mongo - not good
                logger.warn("Item is missing in mongo resource={} id={}".format(endpoint_name, id))
                item = search_backend.find_one(endpoint_name, req=None, _id=id)
                if item:
                    self.remove_from_search(endpoint_name, item)
                raise SuperdeskApiError.notFoundError()
            else:
                # item is there, but no change was done - ok
                logger.warning(
                    "Item was not updated in mongo.",
                    extra=dict(
                        id=id,
                        resource=endpoint_name,
                        updates=updates,
                    ),
                )
                return updates

        if search_backend:
            doc = backend.find_one(endpoint_name, req=None, _id=id)
            if not doc:  # there is no doc in mongo, remove it from elastic
                logger.warn("Item is missing in mongo resource={} id={}".format(endpoint_name, id))
                item = search_backend.find_one(endpoint_name, req=None, _id=id)
                if item:
                    self.remove_from_search(endpoint_name, item)
                raise SuperdeskApiError.notFoundError()
            search_backend.update(endpoint_name, id, doc)

        return updates

    def replace(self, endpoint_name, id, document, original):
        """Replace an item.

        :param endpoint_name: resource name
        :param id: item id
        :param document: next version of item
        :param original: current version of document
        """
        res = self.replace_in_mongo(endpoint_name, id, document, original)
        self.replace_in_search(endpoint_name, id, document, original)
        return res

    def update_in_mongo(self, endpoint_name, id, updates, original):
        """Update item in mongo.

        Modifies ``_updated`` timestamp and ``_etag``.

        :param endpoint_name: resource name
        :param id: item id
        :param updates: updates to item to be saved
        :param original: current version of the item
        """
        updates.setdefault(config.LAST_UPDATED, utcnow())
        if config.ETAG not in updates:
            updated = original.copy()
            updated.update(updates)
            resolve_document_etag(updated, endpoint_name)
            updates[config.ETAG] = updated[config.ETAG]
        backend = self._backend(endpoint_name)
        res = backend.update(endpoint_name, id, updates, original)
        return res if res is not None else updates

    def replace_in_mongo(self, endpoint_name, id, document, original):
        """Replace item in mongo.

        :param endpoint_name: resource name
        :param id: item id
        :param document: next version of item
        :param original: current version of item
        """
        backend = self._backend(endpoint_name)
        res = backend.replace(endpoint_name, id, document, original)
        return res

    def replace_in_search(self, endpoint_name, id, document, original):
        """Replace item in elastic.

        :param endpoint_name: resource name
        :param id: item id
        :param document: next version of item
        :param original: current version of item
        """
        search_backend = self._lookup_backend(endpoint_name)
        if search_backend is not None:
            search_backend.replace(endpoint_name, id, document)

    def delete(self, endpoint_name, lookup):
        """Delete method to delete by using mongo query syntax.

        :param endpoint_name: Name of the endpoint
        :param lookup: User mongo query syntax. example 1. ``{'_id':123}``, 2. ``{'item_id': {'$in': [123, 234]}}``
        :returns: Returns list of ids which were removed.
        """
        docs = list(self.get_from_mongo(endpoint_name, lookup=lookup, req=ParsedRequest()).sort("_id", 1))
        removed_ids = self.delete_docs(endpoint_name, docs)
        if len(docs) and not len(removed_ids):
            logger.warn("No documents for %s resource were deleted using lookup %s", endpoint_name, lookup)
        return removed_ids

    def delete_docs(self, endpoint_name, docs):
        """Delete using list of documents."""
        backend = self._backend(endpoint_name)
        search_backend = self._lookup_backend(endpoint_name)
        ids = [doc[config.ID_FIELD] for doc in docs]
        removed_ids = ids
        logger.info("total documents to be removed {}".format(len(ids)))
        if search_backend and ids:
            removed_ids = []
            # first remove it from search backend, so it won't show up. when this is done - remove it from mongo
            for doc in docs:
                try:
                    self.remove_from_search(endpoint_name, doc)
                    removed_ids.append(doc[config.ID_FIELD])
                except NotFoundError:
                    logger.warning('item missing from elastic _id=%s' % (doc[config.ID_FIELD], ))
                    removed_ids.append(doc[config.ID_FIELD])
                except Exception:
                    logger.exception('item can not be removed from elastic _id=%s' % (doc[config.ID_FIELD], ))
        if len(removed_ids):
            backend.remove(endpoint_name, {config.ID_FIELD: {'$in': removed_ids}})
            logger.info("Removed %d documents from %s.", len(removed_ids), endpoint_name)
        else:
            logger.warn("No documents for %s resource were deleted.", endpoint_name)
        return removed_ids

    def delete_ids_from_mongo(self, endpoint_name, ids):
        """Delete the passed ids from mongo without searching or checking

        :param ids:
        :return:
        """
        backend = self._backend(endpoint_name)
        search_backend = self._lookup_backend(endpoint_name)
        if search_backend:
            raise SuperdeskApiError.forbiddenError(message='Can not remove from endpoint with a defined search')
        backend.remove(endpoint_name, {config.ID_FIELD: {'$in': ids}})
        return len(ids)

    def remove_from_search(self, endpoint_name, doc):
        """Remove document from search backend.

        :param endpoint_name
        :param dict doc: Document to delete
        """
        search_backend = app.data._search_backend(endpoint_name)
        search_backend.remove(endpoint_name,
                              {'_id': doc.get(config.ID_FIELD)},
                              search_backend.get_parent_id(endpoint_name, doc))

    def _datasource(self, endpoint_name):
        return app.data.datasource(endpoint_name)[0]

    def _backend(self, endpoint_name):
        return app.data._backend(endpoint_name)

    def _lookup_backend(self, endpoint_name, fallback=False):
        backend = app.data._search_backend(endpoint_name)
        if backend is None and fallback:
            backend = app.data._backend(endpoint_name)
        return backend

    def set_default_dates(self, doc):
        """Helper to populate ``_created`` and ``_updated`` timestamps."""
        now = utcnow()
        doc.setdefault(config.DATE_CREATED, now)
        doc.setdefault(config.LAST_UPDATED, now)

    def _set_parent(self, endpoint_name, doc, lookup):
        """Set the parent id for parent child document in elastic"""
        search_backend = self._lookup_backend(endpoint_name)
        if search_backend:
            parent = search_backend.get_parent_id(endpoint_name, doc)
            if parent:
                lookup['parent'] = parent

    def _cursor_hook(self, cursor, req):
        """Apply additional methods for cursor"""

        if not req or not req.args:
            return

        # Mongo methods
        if isinstance(cursor, MongoCursor):
            # http://api.mongodb.com/python/current/examples/collations.html
            # https://docs.mongodb.com/manual/reference/collation/
            if 'collation' in req.args:
                cursor.collation(Collation(
                    **std_json.loads(req.args['collation'])
                ))
