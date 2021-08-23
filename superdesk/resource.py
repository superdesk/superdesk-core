# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, List, Optional
import logging

from eve.auth import BasicAuth
from flask_babel.speaklater import LazyString
from typing_extensions import Literal
import superdesk
from eve.utils import config


log = logging.getLogger(__name__)

# elastic mapping helpers
not_indexed = {"type": "string", "index": "no"}  # noqa
not_analyzed = {"type": "string", "index": "not_analyzed"}
not_enabled = {"type": "object", "enabled": False}  # noqa
not_dynamic = {"type": "object", "dynamic": False}  # noqa
text_with_keyword = {
    "type": "text",
    "fields": {
        "keyword": {"type": "keyword"},
    },
}


def build_custom_hateoas(hateoas, doc, **values):
    values.update(doc)
    links = doc.get(config.LINKS)
    if not links:
        links = {}
        doc[config.LINKS] = links

    for link_name in hateoas.keys():
        link = hateoas[link_name]
        link = {"title": link["title"], "href": link["href"]}
        link["href"] = link["href"].format(**values)
        links[link_name] = link


Method = Literal["GET", "POST", "PATCH", "PUT", "DELETE"]
MongoIndexes = Optional[Dict[str, Any]]


class Resource:
    """
    Base model for all endpoints, defines the basic implementation for CRUD datalayer functionality.
    """

    endpoint_name: Optional[str] = None
    url: Optional[str] = None
    item_url: Optional[str] = None
    additional_lookup: Optional[Dict[str, str]] = None
    schema = {}
    allow_unknown: bool = False
    item_methods: Optional[List[Method]] = None
    resource_methods: Optional[List[Method]] = None
    public_methods: Optional[List[Method]] = None
    public_item_methods: Optional[List[Method]] = None
    extra_response_fields: Optional[List[str]] = None
    embedded_fields: Optional[List[str]] = None
    datasource: Dict[str, Any] = {}
    versioning: bool = False
    internal_resource: bool = False
    resource_title: Optional[str] = None
    service: Optional[str] = None
    endpoint_schema: Optional[str] = None
    resource_preferences = None
    etag_ignore_fields: List[str] = []
    mongo_prefix: Optional[str] = None
    mongo_indexes: MongoIndexes = None
    auth_field = None
    authentication: Optional[BasicAuth] = None
    elastic_prefix: Optional[str] = None
    query_objectid_as_string: bool = False
    soft_delete: bool = False
    hateoas = None
    merge_nested_documents: bool = False
    projection: bool = True
    item_privileges = False
    notifications = True

    def __init__(self, endpoint_name, app, service, endpoint_schema=None):
        self.endpoint_name = endpoint_name
        self.service = service
        if not endpoint_schema:
            endpoint_schema = {"schema": self.schema}
            if self.allow_unknown is not None:
                endpoint_schema.update({"allow_unknown": self.allow_unknown})
            if self.additional_lookup is not None:
                endpoint_schema.update({"additional_lookup": self.additional_lookup})
            if self.extra_response_fields is not None:
                endpoint_schema.update({"extra_response_fields": self.extra_response_fields})
            if self.datasource:
                endpoint_schema.update({"datasource": self.datasource})
            if self.item_methods is not None:
                endpoint_schema.update({"item_methods": self.item_methods})
            if self.resource_methods is not None:
                endpoint_schema.update({"resource_methods": self.resource_methods})
            if self.public_methods is not None:
                endpoint_schema.update({"public_methods": self.public_methods})
            if self.public_item_methods is not None:
                endpoint_schema.update({"public_item_methods": self.public_item_methods})
            if self.url is not None:
                endpoint_schema.update({"url": self.url})
            if self.item_url is not None:
                endpoint_schema.update({"item_url": self.item_url})
            if self.embedded_fields is not None:
                endpoint_schema.update({"embedded_fields": self.embedded_fields})
            if self.versioning is not None:
                endpoint_schema.update({"versioning": self.versioning})
            if self.internal_resource is not None:
                endpoint_schema.update({"internal_resource": self.internal_resource})
            if self.resource_title is not None:
                endpoint_schema.update({"resource_title": self.resource_title})
            if self.etag_ignore_fields:
                endpoint_schema.update({"etag_ignore_fields": self.etag_ignore_fields})
            if self.mongo_prefix:
                endpoint_schema.update({"mongo_prefix": self.mongo_prefix})
            if self.auth_field:
                endpoint_schema.update({"auth_field": self.auth_field})
            if self.authentication:
                endpoint_schema.update({"authentication": self.authentication})
            if self.elastic_prefix:
                endpoint_schema.update({"elastic_prefix": self.elastic_prefix})
            if self.query_objectid_as_string:
                endpoint_schema.update({"query_objectid_as_string": self.query_objectid_as_string})
            if self.soft_delete:
                endpoint_schema.update({"soft_delete": self.soft_delete})
            if self.hateoas is not None:
                endpoint_schema.update({"hateoas": self.hateoas})
            if self.merge_nested_documents is not None:
                endpoint_schema.update({"merge_nested_documents": self.merge_nested_documents})
            if self.mongo_indexes:
                # used in app:initialize_data
                endpoint_schema["mongo_indexes__init"] = self.mongo_indexes
            if self.projection is not None:
                endpoint_schema.update({"projection": self.projection})

            endpoint_schema.update(dict(notifications=self.notifications))

            if app.config.get("SCHEMA_UPDATE", {}).get(self.endpoint_name):
                schema_updates = app.config["SCHEMA_UPDATE"][self.endpoint_name]
                log.warning(
                    "Updating {} schema with custom data for fields: {}".format(
                        self.endpoint_name.upper(), ", ".join(schema_updates.keys())
                    )
                )
                self.schema.update(schema_updates)

        self.endpoint_schema = endpoint_schema

        on_fetched_resource = getattr(app, "on_fetched_resource_%s" % self.endpoint_name)
        on_fetched_resource -= service.on_fetched
        on_fetched_resource += service.on_fetched

        on_fetched_item = getattr(app, "on_fetched_item_%s" % self.endpoint_name)
        on_fetched_item -= service.on_fetched_item
        on_fetched_item += service.on_fetched_item

        on_insert_event = getattr(app, "on_insert_%s" % self.endpoint_name)
        on_insert_event -= service.on_create
        on_insert_event += service.on_create

        on_inserted_event = getattr(app, "on_inserted_%s" % self.endpoint_name)
        on_inserted_event -= service.on_created
        on_inserted_event += service.on_created

        on_update_event = getattr(app, "on_update_%s" % self.endpoint_name)
        on_update_event -= service.on_update
        on_update_event += service.on_update

        on_updated_event = getattr(app, "on_updated_%s" % self.endpoint_name)
        on_updated_event -= service.on_updated
        on_updated_event += service.on_updated

        on_replace_event = getattr(app, "on_replace_%s" % self.endpoint_name)
        on_replace_event -= service.on_replace
        on_replace_event += service.on_replace

        on_replaced_event = getattr(app, "on_replaced_%s" % self.endpoint_name)
        on_replaced_event -= service.on_replaced
        on_replaced_event += service.on_replaced

        on_delete_event = getattr(app, "on_delete_item_%s" % self.endpoint_name)
        on_delete_event -= service.on_delete
        on_delete_event += service.on_delete

        on_deleted_event = getattr(app, "on_deleted_item_%s" % self.endpoint_name)
        on_deleted_event -= service.on_deleted
        on_deleted_event += service.on_deleted

        app.register_resource(self.endpoint_name, endpoint_schema)
        superdesk.resources[self.endpoint_name] = self

        for request_method in ["GET", "POST", "PATCH", "PUT", "DELETE"]:
            if hasattr(self, "pre_request_" + request_method.lower()):
                hook_event_name = "on_pre_" + request_method + "_" + self.endpoint_name
                hook_event = getattr(app, hook_event_name)
                hook_method = getattr(self, "pre_request_" + request_method.lower())
                hook_event -= hook_method
                hook_event += hook_method

        # Register callbacks for operations on other resources
        # The callback format is: on_<operation>_res_<other_resource>
        # where <operation> can be: fetched, fetched_item, create, created, update
        # updated, delete, deleted
        operations_events = {
            "fetched": "fetched_resource",
            "fetched_item": "fetched_item",
            "create": "insert",
            "created": "inserted",
            "update": "update",
            "updated": "updated",
            "delete": "delete_item",
            "deleted": "deleted_item",
        }
        for method in [method for method in dir(service) if method.startswith("on_")]:
            for operation, eve_event in operations_events.items():
                method_prefix = "on_%s_res_" % operation
                service_method = getattr(service, method)
                if method.startswith(method_prefix) and callable(service_method):
                    foreign_endpoint_name = method[len(method_prefix) :]
                    if foreign_endpoint_name not in superdesk.resources:
                        raise RuntimeError('Invalid hook "%s" in service "%s"' % (method, type(service)))
                    eve_hook = getattr(app, "on_%s_%s" % (eve_event, foreign_endpoint_name))
                    eve_hook -= service_method
                    eve_hook += service_method

    @staticmethod
    def rel(resource, embeddable=True, required=False, type="objectid", nullable=False, readonly=False):
        return {
            "type": type,
            "required": required,
            "nullable": nullable,
            "readonly": readonly,
            "data_relation": {"resource": resource, "field": "_id", "embeddable": embeddable},
            "mapping": {"type": "keyword"},
        }

    @staticmethod
    def int(required=False, nullable=False):
        return {
            "type": "integer",
            "required": required,
            "nullable": nullable,
        }

    @staticmethod
    def not_analyzed_field(type="string"):
        return {
            "type": type,
            "mapping": not_analyzed,
        }
