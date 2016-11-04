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

from flask import current_app as app, json
from eve.utils import document_etag, config, ParsedRequest
from eve.io.mongo import MongoJSONEncoder
from superdesk.utc import utcnow
from superdesk.logging import logger, item_msg
from eve.methods.common import resolve_document_etag
from elasticsearch.exceptions import RequestError, NotFoundError
from superdesk.errors import SuperdeskApiError


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

    def find(self, endpoint_name, where, max_results=0):
        """Find items for given endpoint using mongo query in python dict object.

        It handles request creation here so no need to do this in service.

        :param string endpoint_name
        :param dict where
        :param int max_results
        """
        req = ParsedRequest()
        req.where = MongoJSONEncoder().encode(where)
        req.max_results = max_results
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

    def get(self, endpoint_name, req, lookup):
        """Get list of items.

        :param endpoint_name: resource name
        :param req: parsed request
        :param lookup: additional filter
        """
        backend = self._lookup_backend(endpoint_name, fallback=True)
        cursor = backend.find(endpoint_name, req, lookup)
        if not cursor.count():
            return cursor  # return 304 if not modified
        else:
            # but fetch without filter if there is a change
            req.if_modified_since = None
            return backend.find(endpoint_name, req, lookup)

    def get_from_mongo(self, endpoint_name, req, lookup):
        """Get list of items from mongo.

        No matter if there is elastic configured, this will use mongo.

        :param endpoint_name: resource name
        :param req: parsed request
        :param lookup: additional filter
        """
        req.if_modified_since = None
        backend = self._backend(endpoint_name)
        return backend.find(endpoint_name, req, lookup)

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
        ids = self.create_in_mongo(endpoint_name, docs, **kwargs)
        self.create_in_search(endpoint_name, docs, **kwargs)
        return ids

    def create_in_mongo(self, endpoint_name, docs, **kwargs):
        """Create items in mongo.

        :param endpoint_name: resource name
        :param docs: list of docs to create
        """
        for doc in docs:
            doc.setdefault(config.ETAG, document_etag(doc))
            self.set_default_dates(doc)

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
        except eve.io.base.DataLayer.OriginalChangedError:
            if not backend.find_one(endpoint_name, req=None, _id=id):
                # item is in elastic, not in mongo - not good
                logger.warn("Item is missing in mongo resource=%s id=%s".format(endpoint_name, id))
                self.remove_from_search(endpoint_name, id)
                raise SuperdeskApiError.notFoundError()
            else:
                # item is there, but no change was done - ok
                logger.exception('Item : {} not updated in collection {}. '
                                 'Updates are : {}'.format(id, endpoint_name, updates))
                return updates

        if search_backend:
            doc = backend.find_one(endpoint_name, req=None, _id=id)
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
        :returns: Returns the mongo remove command response. {'n': 12, 'ok': 1}
        """
        backend = self._backend(endpoint_name)
        search_backend = self._lookup_backend(endpoint_name)
        docs = self.get_from_mongo(endpoint_name, lookup=lookup, req=ParsedRequest())
        ids = [doc[config.ID_FIELD] for doc in docs]
        removed_ids = ids
        logger.info("total documents to be removed {}".format(len(ids)))
        if search_backend and ids:
            removed_ids = []
            # first remove it from search backend, so it won't show up. when this is done - remove it from mongo
            for _id in ids:
                try:
                    self.remove_from_search(endpoint_name, _id)
                    removed_ids.append(_id)
                except NotFoundError:
                    logger.warning('item missing from elastic _id=%s' % (_id, ))
                    removed_ids.append(_id)
                except:
                    logger.exception('item can not be removed from elastic _id=%s' % (_id, ))
        backend.remove(endpoint_name, {config.ID_FIELD: {'$in': removed_ids}})
        logger.info("Removed {} documents from {}.".format(len(ids), endpoint_name))
        if not ids:
            logger.warn("No documents for {} resource were deleted using lookup {}".format(endpoint_name, lookup))

    def remove_from_search(self, endpoint_name, _id):
        """Remove document from search backend.

        :param endpoint_name
        :param _id
        """
        app.data._search_backend(endpoint_name).remove(endpoint_name, {'_id': str(_id)})

    def _datasource(self, endpoint_name):
        return app.data._datasource(endpoint_name)[0]

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
