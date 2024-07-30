# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.metadata.item import CONTENT_STATE, ITEM_PRIORITY, ITEM_URGENCY
from superdesk.workflow import set_default_state
from .common import on_create_item, handle_existing_data
from .archive import update_word_count

from superdesk.core import get_app_config
from superdesk.resource_fields import ITEMS
from superdesk.io.ingest import IngestResource, IngestService  # NOQA
from apps.archive.highlights_search_mixin import HighlightsSearchMixin


class AppIngestService(IngestService, HighlightsSearchMixin):
    def on_fetched(self, docs):
        """Items when ingested have different case for pubstatus.

        Overriding this to handle existing data in Mongo & Elastic
        """

        for item in docs[ITEMS]:
            handle_existing_data(item, doc_type="ingest")

    def on_create(self, docs):
        for doc in docs:
            set_default_state(doc, CONTENT_STATE.INGESTED)
            if not get_app_config("DEFAULT_CONTENT_TYPE", None):
                doc.setdefault(ITEM_PRIORITY, int(get_app_config("DEFAULT_PRIORITY_VALUE_FOR_INGESTED_ARTICLES")))
                doc.setdefault(ITEM_URGENCY, int(get_app_config("DEFAULT_URGENCY_VALUE_FOR_INGESTED_ARTICLES")))
            handle_existing_data(doc, doc_type="ingest")
            update_word_count(doc)

        on_create_item(docs, repo_type="ingest")  # do it after setting the state otherwise it will make it

    def get(self, req, lookup):
        req, lookup = self._get_highlight(req, lookup)
        return super().get(req, lookup)
