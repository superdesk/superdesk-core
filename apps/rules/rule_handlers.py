# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2022 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict
import logging

from eve.utils import config
from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE, MEDIA_TYPES
from superdesk.errors import AlreadyExistsError

logger = logging.getLogger(__name__)


class RoutingRuleHandler:
    NAME: str

    def can_handle(self, rule, ingest_item, routing_scheme) -> bool:
        raise NotImplementedError()

    def apply_rule(self, rule, ingest_item, routing_scheme):
        raise NotImplementedError()


registered_routing_rule_handlers: Dict[str, RoutingRuleHandler] = {}


def register_routing_rule_handler(routing_handler: RoutingRuleHandler):
    if registered_routing_rule_handlers.get(routing_handler.NAME):
        raise AlreadyExistsError(f"Ingest Publisher: {routing_handler.NAME} already registered")

    registered_routing_rule_handlers[routing_handler.NAME] = routing_handler


def get_routing_rule_handler(rule) -> RoutingRuleHandler:
    return registered_routing_rule_handlers[rule.get("handler", DeskFetchPublishRoutingRuleHandler.NAME)]


class DeskFetchPublishRoutingRuleHandler(RoutingRuleHandler):
    NAME = "desk_fetch_publish"

    def can_handle(self, rule, ingest_item, routing_scheme):
        return ingest_item.get(ITEM_TYPE) in (
            MEDIA_TYPES + (CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE)
        )

    def apply_rule(self, rule, ingest_item, routing_scheme):
        if rule.get("actions", {}).get("preserve_desk", False) and ingest_item.get("task", {}).get("desk"):
            desk = get_resource_service("desks").find_one(req=None, _id=ingest_item["task"]["desk"])
            if ingest_item.get("task", {}).get("stage"):
                stage_id = ingest_item["task"]["stage"]
            else:
                stage_id = desk["incoming_stage"]
            self.__fetch(ingest_item, [{"desk": desk[config.ID_FIELD], "stage": stage_id}], rule)
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
                            config.ID_FIELD: ingest_item[config.ID_FIELD],
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
        default_categories = self._get_categories(config.DEFAULT_CATEGORY_QCODES_FOR_AUTO_PUBLISHED_ARTICLES)
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
