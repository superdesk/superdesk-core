# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.services import BaseService
from superdesk.core import get_app_config
from superdesk.resource_fields import ID_FIELD
from superdesk.flask import g, request


class ApiAuditService(BaseService):
    """
    Service class that provides an auditing service for the retrieval of items, assets and packages via the API
    """

    def audit_item(self, item, id):
        """
        Record the retrieval of an item or asset
        :param item: The item to audit
        :param id: id of the item
        :return:
        """
        doc = item.copy()
        doc["_id"] = id
        self._audit_docs([doc])

    def audit_items(self, items):
        self._audit_docs(items)

    def _audit_docs(self, docs):
        if not len(docs):
            return
        if not get_app_config("CONTENTAPI_AUDIT", True):
            return
        subscriber = getattr(g, "user", None)
        # in behave testing we get user (dict)
        if isinstance(subscriber, dict):
            subscriber = subscriber.get(ID_FIELD)
        audit_docs = [
            {
                "type": item.get("type", ""),
                "subscriber": subscriber,
                "uri": item.get("uri", None),
                "items_id": item["_id"],
                "version": item.get("version", ""),
                "remote_addr": request.remote_addr,
            }
            for item in docs
        ]
        self.post(audit_docs)
