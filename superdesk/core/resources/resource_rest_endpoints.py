# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import math
import logging
import traceback

from typing import Optional, cast, Any, Literal
from copy import deepcopy

from dataclasses import dataclass
from pydantic import ValidationError, BaseModel, NonNegativeInt, field_validator
from pydantic_core import PydanticCustomError
from eve.utils import querydef
from typing_extensions import override
from werkzeug.datastructures import MultiDict
from bson import ObjectId

from superdesk.core import json
from superdesk.utils import get_cors_headers
from superdesk.errors import SuperdeskApiError, SuperdeskError
from superdesk.core.app import get_app_config, get_current_async_app
from superdesk.core.types import (
    SearchRequest,
    SearchArgs,
    VersionParam,
    AuthConfig,
    HTTP_METHOD,
    Request,
    Response,
    RestGetResponse,
    ProjectedFieldArg,
)
from superdesk.resource_fields import STATUS, STATUS_OK, STATUS_ERR, ITEMS, ISSUES, ERROR
from superdesk.core.web import RestEndpoints, ItemRequestViewArgs, Endpoint

from .model import ResourceModel
from .resource_config import ResourceConfig
from .validators import get_field_errors_from_pydantic_validation_error
from .utils import combine_projection_args


logger = logging.getLogger("superdesk")


@dataclass
class RestParentLink:
    #: Name of the resource this parent link belongs to
    resource_name: str

    #: Field used to store the resource ID in the child resource, defaults to ``resource_name``
    model_id_field: str | None = None

    #: Name of the URL argument in the route, defaults to ``model_id_field``
    url_arg_name: str | None = None

    #: ID Field of the parent used when searching for parent item resource, defaults to ``model_id_field``
    parent_id_field: str = "_id"

    def get_model_id_field(self) -> str:
        """Get the ID Field for the local model used to store the reference to the parent model"""

        return self.model_id_field or self.resource_name

    def get_url_arg_name(self) -> str:
        """Get the name of hte URL argument used in the route"""

        return self.url_arg_name or self.model_id_field or self.resource_name


@dataclass
class RestEndpointConfig:
    #: Optional list of resource level methods, defaults to ["GET", "POST"]
    resource_methods: list[HTTP_METHOD] | None = None

    #: Optional list of item level methods, defaults to ["GET", "PATCH", "DELETE"]
    item_methods: list[HTTP_METHOD] | None = None

    #: Optional EndpointGroup, will default to `ResourceRestEndpoints`
    endpoints_class: Optional[type["ResourceRestEndpoints"]] = None

    #: Optionally set a custom URL ID param syntax for item routes
    id_param_type: str | None = None

    #: Optionally set a custom URL for routes, defaults to ``resource_name``
    url: str | None = None

    #: Optionally assign parent resource(s) for this resource (parent/child relationship)
    #: This will prepend this resources URL with the URL of the parent resource item
    parent_links: list[RestParentLink] | None = None

    auth: AuthConfig = None

    enable_cors: bool | None = None

    # Optionally populate the item nested hateoas
    populate_item_hateoas: bool | None = None

    #: Exclude these fields from ALL responses (uses MongoDB or Elasticsearch to provide projection)
    #: Raises an exception if client specifically requests any of these fields to be included
    exclude_fields_in_response: list[str] | None = None


def get_id_url_type(data_class: type[ResourceModel]) -> str:
    """Get the URL param type for the ID field for route registration"""

    if data_class.uses_objectid_for_id():
        return 'regex("[a-f0-9]{24}")'
    else:
        return 'regex("[\w,.:_-]+")'


class ItemRequestUrlArgs(BaseModel):
    version: VersionParam | None = None
    page: NonNegativeInt = 1
    max_results: NonNegativeInt = 200
    projection: ProjectedFieldArg | None = None

    @field_validator("projection", mode="before")
    def parse_projection(cls, value: ProjectedFieldArg | str | None) -> ProjectedFieldArg | None:
        try:
            if isinstance(value, str):
                return None if not value else json.loads(value)
            else:
                return value
        except Exception as error:
            # raise error
            raise PydanticCustomError("json", f"Invalid JSON: {error}")


class ResourceRestEndpoints(RestEndpoints):
    """Custom EndpointGroup for REST resources"""

    #: The config for the resource to use
    resource_config: ResourceConfig

    #: REST endpoint config
    endpoint_config: RestEndpointConfig

    def __init__(
        self,
        resource_config: ResourceConfig,
        endpoint_config: RestEndpointConfig,
    ):
        self.resource_config = resource_config
        self.endpoint_config = endpoint_config

        if self.endpoint_config.enable_cors is None:
            # Enable cors by default
            self.endpoint_config.enable_cors = cast(bool, get_app_config("ASYNC_ENABLE_CORS", True))

        if self.endpoint_config.populate_item_hateoas is None:
            # Enable item HATEOAS by default
            self.endpoint_config.populate_item_hateoas = cast(bool, get_app_config("ASYNC_POPULATE_HATEOAS", True))

        super().__init__(
            url=endpoint_config.url or resource_config.name,
            name=resource_config.name,
            import_name=resource_config.__module__,
            resource_methods=endpoint_config.resource_methods,
            item_methods=endpoint_config.item_methods,
            id_param_type=endpoint_config.id_param_type or get_id_url_type(resource_config.data_class),
            auth=endpoint_config.auth,
        )

    def add_endpoints(self):
        if self.endpoint_config.enable_cors:
            self.endpoints.append(
                Endpoint(
                    url=self.get_resource_url(),
                    name="resource_options",
                    func=self.resource_options_endpoint,
                    methods=["OPTIONS"],
                    parent=self,
                )
            )
            self.endpoints.append(
                Endpoint(
                    url=self.get_item_url(),
                    name="item_options",
                    func=self.item_options_endpoint,
                    methods=["OPTIONS"],
                    parent=self,
                )
            )

        super().add_endpoints()

    def get_resource_url(self) -> str:
        """Returns the URL for this resource, for registering with WSGI

        If the resource has ``parent_links`` configured, these will be used to construct the URL
        with the parent resources URL and item ID
        """

        if self.endpoint_config.parent_links is None:
            return self.url

        app = get_current_async_app()
        url = ""
        for parent_link in self.endpoint_config.parent_links:
            parent_config = app.resources.get_config(parent_link.resource_name)
            id_param_type = 'regex("[\w,.:_-]+")'
            parent_url = parent_link.resource_name

            if parent_config.rest_endpoints is not None:
                if parent_config.rest_endpoints.url:
                    parent_url = parent_config.rest_endpoints.url

                if parent_config.rest_endpoints.id_param_type:
                    id_param_type = parent_config.rest_endpoints.id_param_type
                else:
                    id_param_type = get_id_url_type(parent_config.data_class)

            arg_name = parent_link.get_url_arg_name()
            url_prefix = f"{parent_url}/<{id_param_type}:{arg_name}>"
            url += url_prefix + "/"

        return url + self.url

    def get_item_url(self, arg_name: str = "item_id") -> str:
        """Returns the URL for an item of this resource, for registering with WSGI

        :param arg_name: The name of the URL argument to use for the resource item URL
        :return: The URL for an item of this resource
        """

        return f"{self.get_resource_url()}/<{self.id_param_type}:{arg_name}>"

    async def get_parent_items(self, request: Request) -> dict[str, dict]:
        """Returns a dictionary of resource name to item for configured parent links

        :return: A dictionary, with the key being the resource name and value being the parent item
        :raises SuperdeskApiError.badRequestError: If a parent item is not found
        """

        if self.endpoint_config.parent_links is None:
            return {}

        items: dict[str, dict] = {}
        for parent_link in self.endpoint_config.parent_links:
            service = get_current_async_app().resources.get_resource_service(parent_link.resource_name)
            item_id: str | ObjectId | None = request.get_view_args(parent_link.get_url_arg_name())
            if not item_id:
                raise SuperdeskApiError.badRequestError("Parent resource ID not provided in URL")
            elif service.id_uses_objectid():
                item_id = ObjectId(item_id)

            # MyPy complains about this next call, but the args are correct
            item = await service.find_one_raw(use_mongo=True, version=None, **{parent_link.parent_id_field: item_id})  # type: ignore[call-overload]
            if not item:
                raise SuperdeskApiError.notFoundError(
                    f"Parent resource {parent_link.resource_name} with ID '{item_id}' not found"
                )
            items[parent_link.resource_name] = item

        return items

    def construct_parent_item_lookup(self, request: Request) -> dict:
        """Prefills a MongoDB query with the parent attributes from the request

        This is used to filter items of this resource to make sure they belong to all parent item(s).

        :param request: The request object currently being processed
        :return: A MongoDB query
        """
        if self.endpoint_config.parent_links is None:
            return {}

        lookup = {}
        for parent_link in self.endpoint_config.parent_links:
            service = get_current_async_app().resources.get_resource_service(parent_link.resource_name)
            item_id: str | ObjectId | None = request.get_view_args(parent_link.get_url_arg_name())
            if service.id_uses_objectid():
                item_id = ObjectId(item_id)
            lookup[parent_link.get_model_id_field()] = item_id
        return lookup

    @property
    def service(self):
        return get_current_async_app().resources.get_resource_service(self.resource_config.name)

    def get_exclude_fields_projection(self) -> dict[str, Literal[False]] | None:
        if self.endpoint_config.exclude_fields_in_response:
            return cast(
                dict[str, Literal[False]], {field: False for field in self.endpoint_config.exclude_fields_in_response}
            )
        return None

    @override
    async def get_item(
        self,
        args: ItemRequestViewArgs,
        params: ItemRequestUrlArgs,
        request: Request,
    ) -> Response:
        """Processes a get single item request"""

        headers = self.get_item_cors_headers()
        await self.get_parent_items(request)
        signals = self.resource_config.data_class.get_signals()
        await signals.web.on_get.send(request)

        projection_args = combine_projection_args(self.get_exclude_fields_projection(), params.projection)
        if params.version == "all":
            items, count = await self.service.get_all_item_versions(
                args.item_id, params.max_results, params.page, projection=projection_args
            )
            response_data = RestGetResponse(
                _items=items,
                _meta=dict(
                    page=params.page,
                    max_results=params.max_results,
                    total=count,
                ),
                _links=self._build_resource_hateoas(
                    SearchRequest(
                        max_results=params.max_results,
                        page=params.page,
                        args=dict(version=params.version),
                    ),
                    count,
                    request,
                ),
            )
            response = Response(response_data, 200, headers + [("X-Total-Count", count)])
            await signals.web.on_get_response.send(request, response)
            return response
        elif self.endpoint_config.parent_links:
            lookup = self.construct_parent_item_lookup(request)
            lookup["_id"] = args.item_id if not self.service.id_uses_objectid() else ObjectId(args.item_id)
            item = await self.service.find_one_raw(
                use_mongo=True, version=params.version, projection=projection_args, **lookup
            )
        else:
            item = await self.service.find_by_id_raw(args.item_id, params.version, projection=projection_args)

        if not item:
            raise SuperdeskApiError.notFoundError(
                f"{self.resource_config.name} resource with ID '{args.item_id}' not found"
            )

        self._populate_hateoas_if_needed(request, [item])
        await self.on_fetched_item(request, item)
        response = Response(item, 200, headers)

        await signals.web.on_get_response.send(request, response)
        return response

    async def create_item(self, request: Request) -> Response:
        """Processes a create item request"""

        parent_items = await self.get_parent_items(request)
        service = self.service
        payload: dict | list[dict] | None = await request.get_json()

        if payload is None:
            raise SuperdeskApiError.badRequestError("Empty payload")

        if isinstance(payload, dict):
            payload = [payload]

        signals = self.resource_config.data_class.get_signals()
        await signals.web.on_create.send(request, payload)

        model_instances = []
        issues = []
        return_code = 201
        for value in deepcopy(payload):
            # Validate the provided item
            try:
                for parent_link in self.endpoint_config.parent_links or []:
                    parent_item = parent_items.get(parent_link.resource_name)
                    if parent_item is not None:
                        value[parent_link.get_model_id_field()] = parent_item[parent_link.parent_id_field]

                create_response = await service.create([value])
                model_instances.extend(create_response)
            except ValidationError as validation_error:
                return_code = 400
                issues.append(
                    {
                        STATUS: STATUS_ERR,
                        ISSUES: get_field_errors_from_pydantic_validation_error(validation_error),
                    }
                )
                self._log_traceback(validation_error, "Validation error while creating item")

            except SuperdeskError as superdesk_error:
                return_code = superdesk_error.status_code
                # Let the Superdesk exception populate the issue dictionary
                issues.append(
                    {
                        "validation exception": str(superdesk_error),
                        **superdesk_error.to_dict(),
                    }
                )
            except Exception as exception:
                return_code = 400
                issues.append(
                    {
                        STATUS: STATUS_ERR,
                        ISSUES: {"exception": str(exception)},
                    }
                )
                self._log_traceback(exception, "Unexpected exception while creating item")

        if self.endpoint_config.exclude_fields_in_response:
            # If projection is enabled, we fetch all newly created items with projection applied
            # That way projection is applied to all Create request responses
            model_instances = await self.service.find_by_ids(
                [instance.id for instance in model_instances], projection=self.get_exclude_fields_projection()
            )

        results: list[dict]
        results = [
            {
                **self._populate_item_hateoas(
                    request,
                    # make sure to include unset and default values
                    model_instance.to_dict(exclude_defaults=False, exclude_none=True, exclude_unset=False),
                ),
                STATUS: STATUS_OK,
            }
            for model_instance in model_instances
        ]

        results += issues

        if len(results) == 1:
            response_body = results[0]
        else:
            response_body = {
                STATUS: STATUS_OK,
                ITEMS: results,
            }

        num_issues = len(issues)
        if num_issues:
            # If at least one document got issues, the whole request fails and a
            # ``400 Bad Request`` status is return.
            response_body.update(
                {
                    STATUS: STATUS_ERR,
                    ERROR: {
                        "code": return_code,
                        "message": f"Insertion failure: {num_issues} document(s) contain(s) error(s)",
                    },
                }
            )

        response = Response(
            response_body,
            return_code,
            self.get_resource_cors_headers(),
        )

        await signals.web.on_create_response.send(request, response)
        return response

    async def update_item(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: Request,
    ) -> Response:
        """Processes an update item request"""

        if_match = request.get_header("If-Match")
        if self.resource_config.uses_etag and not if_match:
            raise SuperdeskApiError.preconditionRequiredError(
                "To edit a document its etag must be provided using the If-Match header"
            )

        headers = self.get_item_cors_headers()
        await self.get_parent_items(request)
        payload = await request.get_json()

        if not payload:
            raise SuperdeskApiError.badRequestError("Empty payload")

        original = await self.service.find_by_id(args.item_id)
        if original is None:
            raise SuperdeskApiError.notFoundError(
                f"{self.resource_config.name} resource with ID '{args.item_id}' not found"
            )

        signals = self.resource_config.data_class.get_signals()
        issues: dict | None = None
        return_code = 200
        updated: dict | None = None
        response_body: dict | None = None
        try:
            await signals.web.on_update.send(request, original, payload)
            payload = payload.copy()
            updated_instance = await self.service.update(args.item_id, payload, if_match, original)
            if self.endpoint_config.exclude_fields_in_response:
                # If projection is enabled, we fetch the updated item with projection applied
                # That way projection is applied to all Update request responses
                updated = (
                    await self.service.find_by_id(args.item_id, projection=self.get_exclude_fields_projection())
                ).to_dict()
            else:
                updated = updated_instance.to_dict()
        except ValidationError as validation_error:
            return_code = 400
            issues = get_field_errors_from_pydantic_validation_error(validation_error)
            self._log_traceback(validation_error, "Validation error while updating item")

        except SuperdeskError as superdesk_error:
            return_code = superdesk_error.status_code
            # Let the Superdesk exception populate the issue dictionary
            response_body = superdesk_error.to_dict()
            response_body.setdefault(ISSUES, {})["validator exception"] = str(superdesk_error)

        if not response_body:
            if issues is not None or updated is None:
                response_body = {
                    STATUS: STATUS_ERR,
                    ERROR: {"code": return_code, "message": "Update failure: document contains error(s)"},
                    ISSUES: issues,
                }
            else:
                response_body = {
                    **self._populate_item_hateoas(request, updated),
                    STATUS: STATUS_OK,
                }

        response = Response(response_body, return_code, headers)
        await signals.web.on_update_response.send(request, response)
        return response

    async def delete_item(self, args: ItemRequestViewArgs, params: None, request: Request) -> Response:
        """Processes a delete item request"""

        headers = self.get_item_cors_headers()
        await self.get_parent_items(request)
        service = self.service
        original = await service.find_by_id(args.item_id)

        if not original:
            raise SuperdeskApiError.notFoundError(
                f"{self.resource_config.name} resource with ID '{args.item_id}' not found"
            )

        if_match = request.get_header("If-Match")
        if self.resource_config.uses_etag and not if_match:
            raise SuperdeskApiError.preconditionRequiredError(
                "To edit a document its etag must be provided using the If-Match header"
            )

        signals = self.resource_config.data_class.get_signals()
        await signals.web.on_delete.send(request, original)
        await service.delete(original, if_match)
        response = Response({}, 204, headers)
        await signals.web.on_delete_response.send(request, response)
        return response

    def update_where_filter(self, params: SearchRequest, where: dict):
        if not isinstance(params.where, dict):
            if params.where is None:
                params.where = {}
            elif isinstance(params.where, str):
                params.where = cast(dict, json.loads(params.where))

        params.where.update(where)

    async def search_items(
        self,
        args: None,
        params: SearchRequest,
        request: Request,
    ) -> Response:
        """Processes a search request"""

        await self.get_parent_items(request)

        if len(self.endpoint_config.parent_links or []):
            lookup = self.construct_parent_item_lookup(request)
            self.update_where_filter(params, lookup)

        params.args = cast(SearchArgs, params.model_extra)
        signals = self.resource_config.data_class.get_signals()
        await signals.web.on_search.send(request, params)
        params.projection = combine_projection_args(self.get_exclude_fields_projection(), params)
        cursor = await self.service.find(params)
        count = await cursor.count()

        items = await cursor.to_list_raw()
        self._populate_hateoas_if_needed(request, items)

        response_data = RestGetResponse(
            _items=items,
            _meta=dict(
                page=params.page,
                max_results=params.max_results if params.max_results is not None else 25,
                total=count,
            ),
        )

        status = 200
        headers = [("X-Total-Count", count)] + self.get_resource_cors_headers()
        response_data["_links"] = self._build_resource_hateoas(params, count, request)
        if hasattr(cursor, "extra"):
            getattr(cursor, "extra")(response_data)

        response = Response(response_data, status, headers)
        await self.on_fetched(request, response_data)
        await signals.web.on_search_response.send(request, response)
        return response

    async def resource_options_endpoint(self) -> Response:
        return Response("", 200, self.get_resource_cors_headers())

    async def item_options_endpoint(self) -> Response:
        return Response("", 200, self.get_item_cors_headers())

    def get_resource_cors_headers(self):
        if not self.endpoint_config.enable_cors:
            return []

        methods = (self.endpoint_config.resource_methods or ["GET", "POST"]) + ["OPTIONS", "HEAD"]
        return get_cors_headers(", ".join(methods))

    def get_item_cors_headers(self):
        if not self.endpoint_config.enable_cors:
            return []

        methods = (self.endpoint_config.item_methods or ["GET", "PATCH", "DELETE"]) + ["OPTIONS", "HEAD"]
        return get_cors_headers(", ".join(methods))

    def _build_resource_hateoas(self, req: SearchRequest, doc_count: int | None, request: Request) -> dict[str, Any]:
        links = {
            "parent": {
                "title": "home",
                "href": "/",
            },
            "self": {
                "title": self.resource_config.title or self.resource_config.data_class.__name__,
                "href": request.path.strip("/"),
            },
        }

        default_params = [
            "where",
            "sort",
            "page",
            "max_results",
            "embedded",
            "projection",
            "version",
        ]
        other_params: MultiDict = MultiDict(
            (key, value)
            for key, values in MultiDict(req.args or {}).items()
            for value in values
            if key not in default_params
        )

        version = (req.args or {}).get("version")
        q = querydef(req.max_results, req.where, req.sort, version, req.page, other_params)

        if doc_count:
            links["self"]["href"] += q

        pagination_ink = links["self"]["href"].split("?")[0]
        if req.page * req.max_results < (doc_count or 0):
            q = querydef(
                req.max_results,
                req.where,
                req.sort,
                version,
                req.page + 1,
                other_params,
            )
            links["next"] = {"title": "next page", "href": f"{pagination_ink}{q}"}

            if doc_count:
                last_page = int(math.ceil(doc_count / req.max_results))
                q = querydef(
                    req.max_results,
                    req.where,
                    req.sort,
                    version,
                    last_page,
                    other_params,
                )
                links["last"] = {
                    "title": "last page",
                    "href": f"{pagination_ink}{q}",
                }

        if req.page > 1:
            q = querydef(
                req.max_results,
                req.where,
                req.sort,
                version,
                req.page - 1,
                other_params,
            )
            links["prev"] = {
                "title": "previous page",
                "href": f"{pagination_ink}{q}",
            }

        return links

    def _populate_hateoas_if_needed(self, request: Request, items: list[dict[str, Any]]):
        """
        Populate the hateoas information for a list of items only if the
        endpoint config `populate_item_hateoas` flag is set to True
        """

        if not self.endpoint_config.populate_item_hateoas:
            return

        for item in items:
            self._populate_item_hateoas(request, item, force_append_id=True)

    def _populate_item_hateoas(
        self, request: Request, item: dict[str, Any], force_append_id: bool = False
    ) -> dict[str, Any]:
        item.setdefault("_links", {})
        item["_links"]["self"] = {
            "title": self.resource_config.title or self.resource_config.data_class.__name__,
            "href": self.gen_url_for_item(request, item["_id"], force_append_id),
        }

        # extract related links from the `resource_config.data_class` relations (annotations)
        if related_links := self.resource_config.data_class.get_related_links(item):
            item["_links"]["related"] = related_links

        return item

    async def on_fetched_item(self, request: Request, doc: dict) -> None:
        pass

    async def on_fetched(self, request: Request, doc: RestGetResponse) -> None:
        pass

    def _log_traceback(self, exception: Exception, message: str = "Exception occurred") -> None:
        """Logs the exception message and the full traceback."""
        logger.warn(f"{message}: {exception}")
        logger.warn(traceback.format_exc())
