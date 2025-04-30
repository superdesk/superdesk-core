# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any
from collections import namedtuple
import json
import logging

from superdesk.core import get_current_app
from superdesk.types import PublishQueueResource
from superdesk.resource_fields import ID_FIELD, ITEMS, DATE_CREATED, LAST_UPDATED, VERSION
from superdesk.flask import request
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import not_analyzed, ITEM_STATE, PUBLISH_STATES, CONTENT_STATE
from superdesk.metadata.utils import aggregations, get_elastic_highlight_query
from superdesk.resource import Resource
from superdesk.eve_async import AsyncBaseService
from superdesk.utc import utcnow

from bson.objectid import ObjectId
from eve.utils import ParsedRequest

from apps.archive.archive import SOURCE as ARCHIVE
from apps.archive.common import handle_existing_data, item_schema
from superdesk.publish import PUBLISHED_IN_PACKAGE
from superdesk.publish_async.utils import get_next_sequence_number
from apps.content import push_content_notification
from quart_babel import gettext as _
from apps.archive.highlights_search_mixin import HighlightsSearchMixin

logger = logging.getLogger(__name__)

PUBLISHED = "published"
LAST_PUBLISHED_VERSION = "last_published_version"
QUEUE_STATE = "queue_state"
ERROR_MESSAGE = "error_message"
QUEUE_STATES = [
    "pending",
    #: Item is being pushed with ``publish:push``.
    "pushed",
    "in_progress",
    "queued",
    "queued_not_transmitted",
    #: Something went wrong.
    "error",
]
PUBLISH_STATE = namedtuple(
    "PUBLISH_STATE", ["PENDING", "PUSHED", "IN_PROGRESS", "QUEUED", "QUEUED_NOT_TRANSMITTED", "ERROR"]
)(*QUEUE_STATES)

published_item_fields = {
    "item_id": {"type": "string", "mapping": not_analyzed},
    "publish_state": {"type": "string"},
    # last_published_version field is set to true for last published version of the item in the published collection
    # and for the older version is set to false. This field is used to display the last version of the digital copy
    # in the published view.
    LAST_PUBLISHED_VERSION: {"type": "boolean", "default": True},
    QUEUE_STATE: {
        "type": "string",
        "default": "pushed",
        "allowed": QUEUE_STATES,
    },
    ERROR_MESSAGE: {"type": "string"},
    "is_take_item": {  # deprecated
        "type": "boolean",
        "default": False,
    },
    "digital_item_id": {"type": "string"},  # deprecated
    "publish_sequence_no": {"type": "integer", "readonly": True},
    "last_queue_event": {"type": "datetime"},
    # item is moved to legal. True if moved else false.
    "moved_to_legal": {"type": "boolean", "default": False},
    # if item is published as part of a package this will
    # be set to package id so transmitter can handle such
    # items differently
    PUBLISHED_IN_PACKAGE: {
        "type": "string",
    },
    "_current_version": {  # must be set explicitly, there is no versioning
        "type": "integer",
    },
}


def get_content_filter(req=None):
    """Filter out content of stages not visible to current user (if any).

    :return:
    """
    user = get_current_app().get_current_user_dict()
    if user:
        if "invisible_stages" in user:
            stages = user.get("invisible_stages")
        else:
            # TODO-ASYNC[users]: Upgrade to async when updating this module
            stages = get_resource_service("users").get_invisible_stages_ids(user.get("_id"))

        if stages:
            return {"bool": {"must_not": {"terms": {"task.stage": stages}}}}


class PublishedItemResource(Resource):
    datasource = {
        "search_backend": "elastic",
        "aggregations": aggregations,
        "es_highlight": get_elastic_highlight_query,
        "default_sort": [("_updated", -1)],
        # TODO-ASYNC[elastic]: Support async ``elastic_filter_callback``
        "elastic_filter_callback": get_content_filter,
        "projection": {
            "old_version": 0,
            "last_version": 0,
        },
    }

    schema = item_schema(published_item_fields)
    etag_ignore_fields = [ID_FIELD, "highlights", "item_id", LAST_PUBLISHED_VERSION, "moved_to_legal"]

    privileges = {"POST": "publish_queue", "PATCH": "publish_queue"}
    item_methods = ["GET", "PATCH"]
    additional_lookup = {"url": 'regex("[\w,.:-]+")', "field": "item_id"}

    mongo_indexes = {
        "guid_1": ([("guid", 1)], {"background": True}),
        "item_id_1": ([("item_id", 1)], {"background": True}),
        "translation_id_1": ([("translation_id", 1)], {"background": True}),
    }


class PublishedItemService(AsyncBaseService, HighlightsSearchMixin):
    """
    PublishedItemService class is the base class for ArchivedService.
    """

    SEQ_KEY_NAME = "published_item_sequence_no"

    async def on_fetched_async(self, docs):
        """
        Overriding this to enhance the published article with the one in archive collection
        """

        self.enhance_with_archive_items(docs[ITEMS])

    async def on_fetched_item_async(self, doc):
        """
        Overriding this to enhance the published article with the one in archive collection
        """

        self.enhance_with_archive_items([doc])

    async def on_create_async(self, docs):
        """Runs on create.

        An article can be published multiple times in its lifetime. So, it's necessary to preserve the _id which comes
        from archive collection. Also, sets the expiry on the published item and removes the lock information.
        """

        for doc in docs:
            self.raise_if_not_marked_for_publication(doc)
            doc[LAST_UPDATED] = doc[DATE_CREATED] = utcnow()
            await self.set_defaults(doc)

    async def on_update_async(self, updates, original):
        if ITEM_STATE in updates:
            self.raise_if_not_marked_for_publication(updates)

    async def on_updated_async(self, updates, original):
        if "marked_for_user" in updates:
            updated = original.copy()
            updated.update(updates)
            # Send notification on mark-for-user operation
            get_resource_service("archive").handle_mark_user_notifications(updates, original)
            push_content_notification([updated, original])  # see SDBELGA-192

    def raise_if_not_marked_for_publication(self, doc):
        """
        Item should be one of the PUBLISH_STATES. If not raise error.
        """
        if doc.get(ITEM_STATE) not in PUBLISH_STATES and doc.get(ITEM_STATE) != "spiked":
            raise SuperdeskApiError.badRequestError(
                _("Invalid state ({state}) for the Published item.").format(state=doc.get(ITEM_STATE))
            )

    async def set_defaults(self, doc):
        doc["item_id"] = doc[ID_FIELD]
        doc["versioncreated"] = utcnow()
        doc["publish_sequence_no"] = await get_next_sequence_number(self.SEQ_KEY_NAME)
        doc.pop(ID_FIELD, None)
        doc.pop("lock_user", None)
        doc.pop("lock_time", None)
        doc.pop("lock_action", None)
        doc.pop("lock_session", None)

    def enhance_with_archive_items(self, items):
        if items:
            ids = list(set([item.get("item_id") for item in items if item.get("item_id")]))
            archive_items = []
            archive_lookup = {}
            if ids:
                query = {"$and": [{ID_FIELD: {"$in": ids}}]}
                archive_req = ParsedRequest()
                archive_req.max_results = len(ids)
                # can't access published from elastic due filter on the archive resource hence going to mongo
                archive_items = list(get_resource_service(ARCHIVE).get_from_mongo(req=archive_req, lookup=query))

                for item in archive_items:
                    handle_existing_data(item)
                    archive_lookup[item[ID_FIELD]] = item

            for item in items:
                archive_item = archive_lookup.get(item.get("item_id"), {VERSION: item.get(VERSION, 1)})

                updates = {
                    ID_FIELD: item.get("item_id"),
                    "item_id": item.get(ID_FIELD),
                    "lock_user": archive_item.get("lock_user", None),
                    "lock_time": archive_item.get("lock_time", None),
                    "lock_action": archive_item.get("lock_action", None),
                    "lock_session": archive_item.get("lock_session", None),
                    "archive_item": archive_item if archive_item else None,
                }

                if request and request.args.get("published_id") == "1":
                    updates.pop(ID_FIELD)
                    updates.pop("item_id")

                item.update(updates)
                handle_existing_data(item)

    async def on_delete_async(self, doc):
        """Deleting a published item has a workflow which is implemented in remove_expired().

        Overriding to avoid other services from invoking this method accidentally.
        """

        if get_current_app().testing:
            await super().on_delete_async(doc)
        else:
            raise NotImplementedError(
                _("Deleting a published item has a workflow which is implemented in remove_expired().")
            )

    async def delete_action_async(self, lookup=None):
        """Deleting a published item has a workflow which is implemented in remove_expired().

        Overriding to avoid other services from invoking this method accidentally.
        """

        if get_current_app().testing:
            await super().delete_action_async(lookup)
        else:
            raise NotImplementedError(
                _("Deleting a published item has a workflow which is implemented in remove_expired().")
            )

    async def on_deleted_async(self, doc):
        """Deleting a published item has a workflow which is implemented in remove_expired().

        Overriding to avoid other services from invoking this method accidentally.
        """

        if get_current_app().testing:
            await super().on_deleted_async(doc)
        else:
            raise NotImplementedError(
                _("Deleting a published item has a workflow which is implemented in remove_expired().")
            )

    async def get_other_published_items(self, item_id):
        try:
            return await super().get_from_mongo_async(req=None, lookup={"item_id": item_id})
        except Exception:
            return []

    async def get_last_published_version(self, _id):
        """Returns the last published entry for the passed item id

        :param _id:
        :return:
        """
        try:
            query = {
                "query": {
                    "filtered": {
                        "filter": {
                            "bool": {"must": [{"term": {"item_id": _id}}, {"term": {LAST_PUBLISHED_VERSION: True}}]}
                        }
                    }
                }
            }

            request = ParsedRequest()
            request.args = {"source": json.dumps(query), "repo": "published"}
            cursor = await self.get_async(req=request, lookup=None)
            item = await cursor.next()
            return item
        except Exception:
            return None

    async def get_rewritten_items_by_event_story(self, event_id, rewrite_id, rewrite_field):
        """Returns all the rewritten stories from published and archive for a given event and rewrite_id.

        :param str event_id: event id of the document
        :param str rewrite_id: rewrite id of the document
        :param str rewrite_field: field name 'rewrite_of' or 'rewritten_by'
        """
        try:
            query = {
                "query": {
                    "filtered": {
                        "filter": {
                            "bool": {"must": [{"term": {"event_id": event_id}}, {"term": {rewrite_field: rewrite_id}}]}
                        }
                    }
                }
            }

            request = ParsedRequest()
            request.args = {"source": json.dumps(query), "repo": "archive,published"}
            return await (await get_resource_service("search").get_async(req=request, lookup=None)).to_list()
        except Exception:
            return []

    async def is_rewritten_before(self, item_id):
        """Checks if the published item is rewritten before.

        :param _id: item_id of the published item
        :return: True is it is rewritten before
        """
        doc = await self.find_one_async(req=None, item_id=item_id)
        return doc and "rewritten_by" in doc and doc["rewritten_by"]

    async def update_published_items(self, item_id: str, field: str | dict, state: Any | None = None):
        print(f"Updating publish items for {item_id}")
        items = await self.get_other_published_items(item_id)
        updates = field if isinstance(field, dict) else {field: state}
        async for item in items:
            print("Updating published item")
            try:
                await super().system_update_async(ObjectId(item[ID_FIELD]), updates, item)
            except Exception:
                # This part is used in unit testing
                await super().system_update_async(item[ID_FIELD], updates, item)

    async def delete_by_article_id(self, _id):
        """Removes the article from the published collection.

        Removes published queue entries.

        :param str _id: id of the document to be deleted. In mongo, it is the item_id
        """
        lookup = {"item_id": _id}
        await self.delete_async(lookup=lookup)
        await PublishQueueResource.get_service().delete_many({"item_id": _id})

    async def find_one_async(self, req, **lookup):
        item = await super().find_one_async(req, **lookup)
        handle_existing_data(item)

        return item

    async def move_to_archived(self, _id):
        published_items = await (await self.get_from_mongo_async(req=None, lookup={"item_id": _id})).to_list()
        if not published_items:
            return
        get_resource_service("archived").post(published_items)
        await self.delete_by_article_id(_id)

    async def set_moved_to_legal(self, item_id, version, status):
        """Update the legal flag.

        :param str item_id: id of the document
        :param int version: version of the document
        :param boolean status: True if the item is moved to legal else false
        """
        items = await self.get_other_published_items(item_id)

        async for item in items:
            try:
                if item.get(VERSION) <= version and not item.get("moved_to_legal", False):
                    await super().system_update_async(ObjectId(item.get(ID_FIELD)), {"moved_to_legal": status}, item)
            except Exception:
                logger.exception(
                    "Failed to set the moved_to_legal flag " "for item {} and version {}".format(item_id, version)
                )

    async def get_published_items_by_moved_to_legal(self, item_ids, move_to_legal):
        """Get the pulished items where flag is moved.

        :param list item_ids: List of item
        :param bool move_to_legal: move_to_legal boolean flag
        :return: list of published items
        """
        if item_ids:
            try:
                query = {
                    "query": {
                        "filtered": {
                            "filter": {
                                "and": [{"terms": {"item_id": item_ids}}, {"term": {"moved_to_legal": move_to_legal}}]
                            }
                        }
                    }
                }

                request = ParsedRequest()
                request.args = {"source": json.dumps(query)}
                return await (await super().get_async(req=request, lookup=None)).to_list()
            except Exception:
                logger.exception(
                    "Failed to get published items " "by moved to legal: {} -- ids: {}.".format(move_to_legal, item_ids)
                )

        return []

    async def get_async(self, req, lookup):
        req, lookup = self._get_highlight(req, lookup)
        return await super().get_async(req, lookup)
