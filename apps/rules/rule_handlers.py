# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2022 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from typing import Dict, Any
from quart_babel import lazy_gettext, LazyString

from superdesk.core import get_app_config
from superdesk.resource_fields import ID_FIELD
from superdesk import get_resource_service, Resource, Service
from superdesk.metadata.item import CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE, MEDIA_TYPES
from superdesk.utils import ListCursor

logger = logging.getLogger(__name__)


class RoutingRuleHandler:
    ID: str
    NAME: LazyString
    supported_actions: Dict[str, bool]
    supported_configs: Dict[str, bool]
    default_values: Dict[str, Any]

    async def can_handle(self, rule, ingest_item, routing_scheme) -> bool:
        raise NotImplementedError()

    async def apply_rule(self, rule, ingest_item, routing_scheme):
        raise NotImplementedError()


registered_routing_rule_handlers: Dict[str, RoutingRuleHandler] = {}


def register_routing_rule_handler(routing_handler: RoutingRuleHandler):
    registered_routing_rule_handlers[routing_handler.ID] = routing_handler


def get_routing_rule_handler(rule) -> RoutingRuleHandler:
    return registered_routing_rule_handlers[rule.get("handler", DeskFetchPublishRoutingRuleHandler.ID)]


class IngestRuleHandlersResource(Resource):
    item_methods = []
    resource_methods = ["GET"]
    schema = {
        "_id": {"type": "string"},
        "name": {"type": "string"},
        "supported_actions": {
            "type": "dict",
            "required": False,
            "schema": {},
            "allow_unknown": True,
        },
        "supported_configs": {
            "type": "dict",
            "required": False,
            "schema": {},
            "allow_unknown": True,
        },
        "default_values": {
            "type": "dict",
            "required": False,
            "schema": {},
            "allow_unknown": True,
        },
    }


class IngestRuleHandlersService(Service):
    def get(self, req, lookup):
        """Return list of available ingest rule handlers"""

        values = sorted(
            [
                dict(
                    _id=handler.ID,
                    name=handler.NAME,
                    supported_actions=handler.supported_actions,
                    supported_configs=handler.supported_configs,
                    default_values=handler.default_values,
                )
                for handler in registered_routing_rule_handlers.values()
            ],
            key=lambda x: x["name"].lower(),
        )

        return ListCursor(values)


class DeskFetchPublishRoutingRuleHandler(RoutingRuleHandler):
    ID = "desk_fetch_publish"
    NAME = lazy_gettext("Desk Fetch/Publish")
    supported_actions = {
        "fetch_to_desk": True,
        "publish_from_desk": True,
    }
    supported_configs = {"exit": True, "preserve_desk": True}
    default_values = {
        "name": "",
        "handler": "desk_fetch_publish",
        "filter": None,
        "actions": {
            "fetch": [],
            "publish": [],
            "exit": False,
        },
        "schedule": {
            "day_of_week": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
            "hour_of_day_from": None,
            "hour_of_day_to": None,
            "_allDay": True,
        },
    }

    async def can_handle(self, rule, ingest_item, routing_scheme):
        return ingest_item.get(ITEM_TYPE) in (
            MEDIA_TYPES + (CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE)
        )

    async def apply_rule(self, rule, ingest_item, routing_scheme):
        if rule.get("actions", {}).get("preserve_desk", False) and ingest_item.get("task", {}).get("desk"):
            desk = get_resource_service("desks").find_one(req=None, _id=ingest_item["task"]["desk"])
            if ingest_item.get("task", {}).get("stage"):
                stage_id = ingest_item["task"]["stage"]
            else:
                stage_id = desk["incoming_stage"]
            self.__fetch(ingest_item, [{"desk": desk[ID_FIELD], "stage": stage_id}], rule)
            fetch_actions = [
                f for f in rule.get("actions", {}).get("fetch", []) if f.get("desk") != ingest_item["task"]["desk"]
            ]
        else:
            fetch_actions = rule.get("actions", {}).get("fetch", [])

        self.__fetch(ingest_item, fetch_actions, rule)
        self.__publish(ingest_item, rule.get("actions", {}).get("publish", []), rule)

    def __fetch(self, ingest_item, destinations, rule):
        """Fetch to item to the destinations

        :param item: item to be fetched
        :param destinations: list of desk and stage
        """
        archive_items = []
        for destination in destinations:
            try:
                logger.info("Fetching item %s to desk %s" % (ingest_item.get("guid"), destination))
                target = self.__get_target(destination)
                item_id = get_resource_service("fetch").fetch(
                    [
                        {
                            ID_FIELD: ingest_item[ID_FIELD],
                            "desk": str(destination.get("desk")),
                            "stage": str(destination.get("stage")),
                            "state": CONTENT_STATE.ROUTED,
                            "macro": destination.get("macro", None),
                            "target": target,
                        },
                    ],
                    macro_kwargs={
                        "rule": rule,
                    },
                )[0]
                archive_items.append(item_id)
                logger.info("Fetched item %s to desk %s" % (ingest_item.get("guid"), destination))
            except Exception:
                logger.exception("Failed to fetch item %s to desk %s" % (ingest_item.get("guid"), destination))

        return archive_items

    def __publish(self, ingest_item, destinations, rule):
        """Fetches the item to the desk and then publishes the item.

        :param item: item to be published
        :param destinations: list of desk and stage
        """
        guid = ingest_item.get("guid")
        items_to_publish = self.__fetch(ingest_item, destinations, rule)
        for item in items_to_publish:
            try:
                archive_item = get_resource_service("archive").find_one(req=None, _id=item)
                if archive_item.get("auto_publish") is False:
                    logger.info("Stop auto publishing of item %s", guid)
                    continue
                logger.info("Publishing item %s", guid)
                self._set_default_values(archive_item)
                get_resource_service("archive_publish").patch(item, {"auto_publish": True})
                logger.info("Published item %s", guid)
            except Exception:
                logger.exception("Failed to publish item %s.", guid)

    def __get_target(self, destination):
        """Get the target for destination

        :param dict destination: routing destination
        :return dict: returns target information
        """
        target = {}
        if destination.get("target_subscribers"):
            target["target_subscribers"] = destination.get("target_subscribers")

        if destination.get("target_types"):
            target["target_types"] = destination.get("target_types")

        return target

    def _set_default_values(self, archive_item):
        """Assigns the default values to the item that about to be auto published"""
        default_categories = self._get_categories(get_app_config("DEFAULT_CATEGORY_QCODES_FOR_AUTO_PUBLISHED_ARTICLES"))
        default_values = self._assign_default_values(archive_item, default_categories)
        get_resource_service("archive").patch(archive_item["_id"], default_values)

    def _assign_default_values(self, archive_item, default_categories):
        """Assigns the default values to the item that about to be auto published"""

        default_values = {}
        default_values["headline"] = archive_item.get("headline") or " "

        if archive_item.get("anpa_category"):
            default_values["anpa_category"] = archive_item.get("anpa_category")
        else:
            default_values["anpa_category"] = default_categories

        default_values["slugline"] = archive_item.get("slugline") or " "
        default_values["body_html"] = archive_item.get("body_html") or "<p></p>"
        return default_values

    def _get_categories(self, qcodes):
        """Returns list of categories for a given comma separated qcodes"""

        if not qcodes:
            return

        qcode_list = qcodes.split(",")
        selected_categories = None
        categories = get_resource_service("vocabularies").find_one(req=None, _id="categories")

        if categories and len(qcode_list) > 0:
            selected_categories = []
            for qcode in qcode_list:
                selected_categories.extend(
                    [
                        {"qcode": qcode, "name": c.get("name", "")}
                        for c in categories["items"]
                        if c["is_active"] is True and qcode.lower() == c["qcode"].lower()
                    ]
                )

        return selected_categories


register_routing_rule_handler(DeskFetchPublishRoutingRuleHandler())
