# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import logging

from copy import deepcopy

from superdesk import get_resource_service
from eve.utils import ParsedRequest, config
from superdesk.utils import ListCursor
from superdesk.resource import Resource, build_custom_hateoas
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from superdesk.publish import SUBSCRIBER_TYPES  # NOQA
from flask import current_app as app
from superdesk.metadata.utils import ProductTypes
from superdesk.notification import push_notification


logger = logging.getLogger(__name__)


class SubscribersResource(Resource):
    schema = {
        "name": {"type": "string", "iunique": True, "required": True, "nullable": False, "empty": False},
        "media_type": {"type": "string"},
        "subscriber_type": {"type": "string", "allowed": tuple(SUBSCRIBER_TYPES), "required": True},
        "sequence_num_settings": {
            "type": "dict",
            "schema": {"min": {"type": "integer"}, "max": {"type": "integer"}},
            "required": True,
        },
        "email": {"type": "string", "empty": False, "multiple_emails": True, "required": True},
        "is_active": {"type": "boolean", "default": True},
        "is_targetable": {"type": "boolean", "default": True},
        "critical_errors": {"type": "dict", "valueschema": {"type": "boolean"}},
        "last_closed": {
            "type": "dict",
            "schema": {
                "closed_at": {"type": "datetime"},
                "closed_by": Resource.rel("users", nullable=True),
                "message": {"type": "string"},
            },
        },
        "destinations": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string", "required": True, "empty": False},
                    "format": {"type": "string", "required": True},
                    "preview_endpoint_url": {"type": "string"},
                    "delivery_type": {"type": "string", "required": True},
                    "config": {"type": "dict"},
                },
            },
        },
        "products": {"type": "list", "schema": Resource.rel("products", True)},
        "codes": {"type": "string"},
        "global_filters": {"type": "dict", "valueschema": {"type": "boolean"}},
        "content_api_token": {
            "type": "string",
        },
        "api_products": {"type": "list", "schema": Resource.rel("products", True)},
        "async": {
            "type": "boolean",
            "nullable": True,
        },
        "priority": {
            "type": "boolean",
            "nullable": True,
        },
        "filter_conditions": {
            "type": "list",
        },
        "content_filters": {
            "type": "list",
        },
        "selected_subscribers": {
            "type": "list",
        },
        "init_version": {"type": "integer"},
    }

    item_methods = ["GET", "PATCH", "PUT"]

    privileges = {"POST": "subscribers", "PATCH": "subscribers"}

    mongo_indexes = {
        "name_1": ([("name", 1)], {"unique": True}),
    }


class SubscribersService(BaseService):
    def get(self, req, lookup):
        if req is None:
            req = ParsedRequest()
        if req.args and req.args.get("filter_condition"):
            filter_condition = json.loads(req.args.get("filter_condition"))
            return ListCursor(self._get_subscribers_by_filter_condition(filter_condition))
        return super().get(req=req, lookup=lookup)

    def on_create(self, docs):
        for doc in docs:
            self._validate_seq_num_settings(doc)
            self._validate_products_destinations(doc)

    def on_created(self, docs):
        push_notification("subscriber:create", _id=[doc.get(config.ID_FIELD) for doc in docs])

    def on_update(self, updates, original):
        self._validate_seq_num_settings(updates)
        subscriber = deepcopy(original)
        subscriber.update(updates)
        self._validate_products_destinations(subscriber)

    def on_updated(self, updates, original):
        push_notification("subscriber:update", _id=[original.get(config.ID_FIELD)])

    def on_deleted(self, doc):
        get_resource_service("sequences").delete(
            lookup={"key": "ingest_providers_{_id}".format(_id=doc[config.ID_FIELD])}
        )

    def is_async(self, subscriber_id):
        subscriber = self.find_one(req=None, _id=subscriber_id)
        return subscriber and bool(subscriber.get("async", False))

    def _get_subscribers_by_filter_condition(self, filter_condition):
        """
        Searches all subscribers that has a content filter with the given filter condition

        If filter condition is used in a global filter then it returns all
        subscribers that not disabled the global filter.
        :param filter_condition: Filter condition to test
        :return: List of subscribers
        """
        req = ParsedRequest()
        all_subscribers = list(super().get(req=req, lookup=None))
        selected_products = {}
        selected_subscribers = {}
        selected_content_filters = {}

        filter_condition_service = get_resource_service("filter_conditions")
        content_filter_service = get_resource_service("content_filters")
        product_service = get_resource_service("products")

        existing_products = list(product_service.get(req=req, lookup=None))
        existing_filter_conditions = filter_condition_service.check_similar(filter_condition)
        for fc in existing_filter_conditions:
            existing_content_filters = content_filter_service.get_content_filters_by_filter_condition(fc["_id"])
            for pf in existing_content_filters:
                selected_content_filters[pf["_id"]] = pf

                if pf.get("is_global", False):
                    for s in all_subscribers:
                        gfs = s.get("global_filters", {})
                        if gfs.get(str(pf["_id"]), True):
                            build_custom_hateoas({"self": {"title": "subscribers", "href": "/subscribers/{_id}"}}, s)
                            selected_subscribers[s["_id"]] = s

                for product in existing_products:
                    if (
                        product.get("content_filter")
                        and "filter_id" in product["content_filter"]
                        and product["content_filter"]["filter_id"] == pf["_id"]
                    ):
                        selected_products[product["_id"]] = product

                for s in all_subscribers:
                    all_subscriber_products = list(set(s.get("products") or []) | set(s.get("api_products") or []))
                    for p in all_subscriber_products:
                        if p in selected_products:
                            build_custom_hateoas({"self": {"title": "subscribers", "href": "/subscribers/{_id}"}}, s)
                            selected_subscribers[s["_id"]] = s

        res = {
            "filter_conditions": existing_filter_conditions,
            "content_filters": list(selected_content_filters.values()),
            "products": list(selected_products.values()),
            "selected_subscribers": list(selected_subscribers.values()),
        }
        return [res]

    def _validate_products_destinations(self, subscriber):
        """Validates the subscribers
            1. At least one destination or one api_products is specified.
            2. If direct products are specified then at least one destination is specified.
        :param dict subscriber:
        :return:
        """
        if not subscriber.get("is_active"):
            return

        if not subscriber.get("destinations") and not subscriber.get("api_products"):
            raise SuperdeskApiError.badRequestError(
                payload={"destinations": {"required": 1}, "api_products": {"required": 1}},
                message="At least one destination or one API Product should " "be specified",
            )

        if len(subscriber.get("products") or []) and not subscriber.get("destinations"):
            raise SuperdeskApiError.badRequestError(
                payload={"destinations": {"required": 1}}, message="Destinations not specified."
            )

        if subscriber.get("products"):
            lookup = {config.ID_FIELD: {"$in": subscriber.get("products")}, "product_type": ProductTypes.API.value}
            products = get_resource_service("products").get_product_names(lookup)
            if products:
                raise SuperdeskApiError.badRequestError(
                    payload={"products": 1}, message="Invalid Product Type. " "Products {}.".format(", ".join(products))
                )
        if subscriber.get("api_products"):
            lookup = {
                config.ID_FIELD: {"$in": subscriber.get("api_products")},
                "product_type": ProductTypes.DIRECT.value,
            }
            products = get_resource_service("products").get_product_names(lookup)
            if products:
                raise SuperdeskApiError.badRequestError(
                    payload={"products": 1},
                    message="Invalid Product Type. " "API Products {}.".format(", ".join(products)),
                )

    def get_subscriber_names(self, lookup):
        """Get the subscriber names based on the lookup.
        :param dict lookup: search criteria
        :return list: list of subscriber name
        """
        subscribers = list(self.get(req=None, lookup=lookup))
        return [subscriber["name"] for subscriber in subscribers]

    def _validate_seq_num_settings(self, subscriber):
        """
        Validates the 'sequence_num_settings' property if present in subscriber.

        Below are the validation rules:
            1.  If min value is present then it should be greater than 0
            2.  If min is present and max value isn't available then it's defaulted to MAX_VALUE_OF_PUBLISH_SEQUENCE

        :return: True if validation succeeds otherwise return False.
        """

        if subscriber.get("sequence_num_settings"):
            min = subscriber.get("sequence_num_settings").get("min", 1)
            max = subscriber.get("sequence_num_settings").get("max", app.config["MAX_VALUE_OF_PUBLISH_SEQUENCE"])

            if min <= 0:
                raise SuperdeskApiError.badRequestError(
                    payload={"sequence_num_settings.min": 1},
                    message="Value of Minimum in Sequence Number Settings should " "be greater than 0",
                )

            if min >= max:
                raise SuperdeskApiError.badRequestError(
                    payload={"sequence_num_settings.min": 1},
                    message="Value of Minimum in Sequence Number Settings should " "be less than the value of Maximum",
                )

            del subscriber["sequence_num_settings"]
            subscriber["sequence_num_settings"] = {"min": min, "max": max}

        return True

    def generate_sequence_number(self, subscriber):
        """
        Generates Published Sequence Number for the passed subscriber
        """

        assert subscriber is not None, "Subscriber can't be null"
        min_seq_number = 1
        max_seq_number = app.config["MAX_VALUE_OF_PUBLISH_SEQUENCE"]
        if subscriber.get("sequence_num_settings"):
            min_seq_number = subscriber["sequence_num_settings"]["min"]
            max_seq_number = subscriber["sequence_num_settings"]["max"]

        return get_resource_service("sequences").get_next_sequence_number(
            key_name="subscribers_{_id})".format(_id=subscriber[config.ID_FIELD]),
            max_seq_number=max_seq_number,
            min_seq_number=min_seq_number,
        )
