# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : MarkLark86
# Creation: 2019-12-10 08:57

from superdesk import get_resource_service
from superdesk.commands.data_updates import DataUpdate as _DataUpdate
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

COVERAGE_PROVIDERS = "coverage_providers"
CONTACT_TYPE = "contact_type"

CVS = {
    "coverage_providers": {
        "schema": {"name": {"required": True, "type": "string"}, "qcode": {"required": True, "type": "string"}}
    },
    "contact_type": {
        "_id": "contact_type",
        "unique_field": "qcode",
        "type": "manageable",
        "display_name": "Contact Types",
        "selection_type": "do not show",
        "schema": {
            "name": {"required": True, "type": "string"},
            "qcode": {"required": True, "type": "string"},
            "assignable": {"required": False, "type": "bool", "label": "Assignable"},
        },
        "items": [],
    },
}

CONTACT_TYPE_LINK = {"required": False, "type": "string", "link_vocab": "contact_type", "link_field": "qcode"}


class DataUpdate(_DataUpdate):
    """Add 'contact_type' and update 'coverage_providers' CVs

    Refer to https://dev.sourcefabric.org/browse/SDESK-4766 for more information
    """

    resource = "vocabularies"

    def forwards(self, mongodb_collection, mongodb_database):
        self._add_contact_type_to_coverage_providers(mongodb_collection)
        self._add_contact_type_cv(mongodb_collection)

    def backwards(self, mongodb_collection, mongodb_database):
        self._remove_contact_type_from_coverage_providers(mongodb_collection)
        self._remove_contact_type_cv(mongodb_collection)

    def _add_contact_type_to_coverage_providers(self, mongodb_collection):
        coverage_providers = mongodb_collection.find_one({"_id": COVERAGE_PROVIDERS})

        if not coverage_providers:
            logger.info('"{}" CV not found. Not need to continue'.format(COVERAGE_PROVIDERS))
            return

        schema = coverage_providers.get("schema") or deepcopy(CVS[COVERAGE_PROVIDERS]["schema"])

        if not schema.get("contact_type"):
            schema["contact_type"] = CONTACT_TYPE_LINK

        items = coverage_providers.get("items") or []
        for item in items:
            if not item.get("contact_type"):
                item["contact_type"] = ""

        mongodb_collection.update({"_id": COVERAGE_PROVIDERS}, {"$set": {"schema": schema, "items": items}})

    def _remove_contact_type_from_coverage_providers(self, mongodb_collection):
        coverage_providers = mongodb_collection.find_one({"_id": COVERAGE_PROVIDERS})

        if not coverage_providers:
            logger.info('"{}" CV not found. Not need to continue'.format(COVERAGE_PROVIDERS))
            return

        schema = coverage_providers.get("schema") or deepcopy(CVS[COVERAGE_PROVIDERS]["schema"])
        schema.pop("contact_type", None)

        items = coverage_providers.get("items") or []
        for item in items:
            item.pop("contact_type", None)

        mongodb_collection.update({"_id": COVERAGE_PROVIDERS}, {"$set": {"schema": schema, "items": items}})

    def _add_contact_type_cv(self, mongodb_collection):
        if mongodb_collection.find_one({"_id": CONTACT_TYPE}):
            logger.info('"{}" CV already defined. Nothing to do'.format(CONTACT_TYPE))
            return

        get_resource_service(self.resource).post([CVS[CONTACT_TYPE]])

    def _remove_contact_type_cv(self, mongodb_collection):
        if not mongodb_collection.find_one({"_id": CONTACT_TYPE}):
            logger.info('"{}" CV not defined. Nothing to do'.format(CONTACT_TYPE))
            return

        get_resource_service(self.resource).delete_action({"_id": CONTACT_TYPE})
