# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from flask import g
from superdesk.resource import Resource
from superdesk.services import BaseService

log = logging.getLogger(__name__)


class AuditResource(Resource):
    endpoint_name = "audit"
    resource_methods = ["GET"]
    item_methods = ["GET"]
    notifications = False
    schema = {
        "resource": {"type": "string"},
        "action": {"type": "string"},
        "audit_id": {"type": "string"},
        "extra": {"type": "dict"},
        "user": Resource.rel("users", False),
    }
    exclude = {endpoint_name, "activity", "dictionaries", "macros", "archive_history", "formatters"}


class AuditService(BaseService):
    def on_generic_inserted(self, resource, docs):
        if resource in AuditResource.exclude:
            return

        user = getattr(g, "user", None)
        if not user:
            if resource == "auth":
                user_id = docs[0].get("user")
            else:
                return
        else:
            user_id = user.get("_id")

        if not len(docs):
            return

        audit = {
            "user": user_id,
            "resource": resource,
            "action": "created",
            "extra": docs[0],
            "audit_id": self._extract_doc_id(docs[0]),
        }

        self.post([audit])

    def on_generic_updated(self, resource, doc, original):
        if resource in AuditResource.exclude:
            return

        user = getattr(g, "user", None)
        if not user:
            return

        audit = {
            "user": user.get("_id"),
            "resource": resource,
            "action": "updated",
            "extra": doc,
            "audit_id": self._extract_doc_id(doc) if self._extract_doc_id(doc) else self._extract_doc_id(original),
        }
        if "_id" not in doc:
            audit["extra"]["_id"] = original.get("_id", None)
        self.post([audit])

    def on_generic_deleted(self, resource, doc):
        if resource in AuditResource.exclude:
            return

        user = getattr(g, "user", None)
        if not user:
            return

        audit = {
            "user": user.get("_id"),
            "resource": resource,
            "action": "deleted",
            "extra": doc,
            "audit_id": self._extract_doc_id(doc),
        }
        self.post([audit])

    def _extract_doc_id(self, doc):
        """
        Given an audit item try to extract the id of the item that it relates to
        :param item:
        :return:
        """
        try:
            id = doc.get("_id", doc.get("guid", doc.get("item_id", doc.get("item", None))))
            # do not return an id for items that have a dictionary id
            if not isinstance(id, dict):
                return id
            else:
                None
        except Exception:
            return None
        return None
