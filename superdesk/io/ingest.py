# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource_fields import ID_FIELD
from superdesk.resource import Resource
from superdesk.eve_async import AsyncBaseService
from superdesk.metadata.item import metadata_schema
from superdesk.metadata.utils import extra_response_fields, item_url, aggregations, get_elastic_highlight_query
from eve.methods.common import resolve_document_etag

from superdesk.core import get_app_config, get_current_app
from apps.auth import get_user
from superdesk.notification import push_notification
from superdesk.privilege import GLOBAL_SEARCH_PRIVILEGE
from superdesk.publish_async.utils import get_next_sequence_number

SOURCE = "ingest"


class IngestResource(Resource):
    schema = {"archived": {"type": "datetime"}}
    schema.update(metadata_schema)
    extra_response_fields = extra_response_fields
    item_url = item_url
    datasource = {
        "search_backend": "elastic",
        "aggregations": aggregations,
        "es_highlight": get_elastic_highlight_query,
    }
    privileges = {"DELETE": "fetch", "GET": GLOBAL_SEARCH_PRIVILEGE}
    mongo_indexes = {
        "guid_1": ([("guid", 1)], {"background": True}),
    }


class IngestService(AsyncBaseService):
    async def post_in_mongo_async(self, docs, **kwargs):
        for doc in docs:
            self._resolve_defaults(doc)
        await self.on_create_async(docs)
        resolve_document_etag(docs, self.datasource)
        ids = await self.backend.create_in_mongo_async(self.datasource, docs, **kwargs)
        await self.on_created_async(docs)
        return ids

    async def patch_in_mongo_async(self, id, document, original):
        res = await self.backend.update_in_mongo_async(self.datasource, id, document, original)
        return res

    async def set_ingest_provider_sequence_async(self, item, provider):
        """Sets the value of ingest_provider_sequence in item.

        :param item: object to which ingest_provider_sequence to be set
        :param provider: ingest_provider object, used to build the key name of sequence
        """
        sequence_number = await get_next_sequence_number(
            key_name="ingest_providers_{_id}".format(_id=provider[ID_FIELD]),
            max_seq_number=get_app_config("MAX_VALUE_OF_INGEST_SEQUENCE"),
        )
        item["ingest_provider_sequence"] = str(sequence_number)

    async def on_deleted_async(self, docs):
        docs = docs if isinstance(docs, list) else [docs]
        file_ids = [
            rend.get("media")
            for doc in docs
            for rend in doc.get("renditions", {}).values()
            if not doc.get("archived") and rend.get("media")
        ]

        app = get_current_app()
        for file_id in file_ids:
            await app.media.delete_async(file_id)

        ids = [
            ref.get("residRef")
            for doc in docs
            for group in doc.get("groups", {})
            for ref in group.get("refs", {})
            if ref.get("residRef")
        ]

        if ids:
            await self.delete_async({"_id": {"$in": ids}})

        user = get_user(required=True)
        if docs:
            push_notification("item:deleted", item=str(docs[0].get(ID_FIELD)), user=str(user))

    def should_update(self, old_item, new_item, provider):
        return True
