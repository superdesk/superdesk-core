# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import List, Optional, cast, Dict, Any, Type
import math

from dataclasses import dataclass
from pydantic import ValidationError, BaseModel, NonNegativeInt
from eve.utils import querydef
from typing_extensions import override
from werkzeug.datastructures import MultiDict
from bson import ObjectId

from superdesk.core import json
from superdesk.core.app import get_current_async_app
from superdesk.core.types import SearchRequest, SearchArgs, VersionParam
from superdesk.errors import SuperdeskApiError

from ..web.types import HTTP_METHOD, Request, Response, RestGetResponse
from ..web.rest_endpoints import RestEndpoints, ItemRequestViewArgs

from .model import ResourceConfig, ResourceModel
from .validators import convert_pydantic_validation_error_for_response


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
    resource_methods: Optional[List[HTTP_METHOD]] = None

    #: Optional list of item level methods, defaults to ["GET", "PATCH", "DELETE"]
    item_methods: Optional[List[HTTP_METHOD]] = None

    #: Optional EndpointGroup, will default to `ResourceRestEndpoints`
    endpoints_class: Optional[Type["ResourceRestEndpoints"]] = None

    #: Optionally set a custom URL ID param syntax for item routes
    id_param_type: Optional[str] = None

    #: Optionally set a custom URL for routes, defaults to ``resource_name``
    url: str | None = None

    #: Optionally assign parent resource(s) for this resource (parent/child relationship)
    #: This will prepend this resources URL with the URL of the parent resource item
    parent_links: list[RestParentLink] | None = None


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
        super().__init__(
            url=endpoint_config.url or resource_config.name,
            name=resource_config.name,
            import_name=resource_config.__module__,
            resource_methods=endpoint_config.resource_methods,
            item_methods=endpoint_config.item_methods,
            id_param_type=endpoint_config.id_param_type or get_id_url_type(resource_config.data_class),
        )

    def get_resource_url(self) -> str:
        """Returns the URL for this resource

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
        """Returns the URL for an item of this resource

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
            item_id = request.get_view_args(parent_link.get_url_arg_name())
            if not item_id:
                raise SuperdeskApiError.badRequestError("Parent resource ID not provided in URL")
            item = await service.find_one_raw(use_mongo=True, version=None, **{parent_link.parent_id_field: item_id})
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

    @override
    async def get_item(
        self,
        args: ItemRequestViewArgs,
        params: ItemRequestUrlArgs,
        request: Request,
    ) -> Response:
        """Processes a get single item request"""

        await self.get_parent_items(request)
        service = self.service

        if params.version == "all":
            items, count = await self.service.get_all_item_versions(args.item_id, params.max_results, params.page)
            response = RestGetResponse(
                _items=items,
                _meta=dict(
                    page=params.page,
                    max_results=params.max_results,
                    total=count,
                ),
                _links=self._build_hateoas(
                    SearchRequest(
                        max_results=params.max_results,
                        page=params.page,
                        args=dict(version=params.version),
                    ),
                    count,
                    request,
                ),
            )
            return Response(response, 200, [("X-Total-Count", count)])
        elif self.endpoint_config.parent_links:
            lookup = self.construct_parent_item_lookup(request)
            lookup["_id"] = args.item_id if not service.id_uses_objectid() else ObjectId(args.item_id)
            item = await service.find_one_raw(use_mongo=True, version=params.version, **lookup)
        else:
            item = await service.find_by_id_raw(args.item_id, params.version)

        if not item:
            raise SuperdeskApiError.notFoundError(
                f"{self.resource_config.name} resource with ID '{args.item_id}' not found"
            )

        return Response(
            body=item,
            status_code=200,
            headers=(),
        )

    async def create_item(self, request: Request) -> Response:
        """Processes a create item request"""

        parent_items = await self.get_parent_items(request)
        service = self.service
        payload = await request.get_json()

        if payload is None:
            raise SuperdeskApiError.badRequestError("Empty payload")

        if isinstance(payload, dict):
            payload = [payload]

        model_instances = []
        for value in payload:
            # Validate the provided item,
            try:
                if "_id" not in value:
                    value["_id"] = service.generate_id()

                for parent_link in self.endpoint_config.parent_links or []:
                    parent_item = parent_items.get(parent_link.resource_name)
                    if parent_item is not None:
                        value[parent_link.get_model_id_field()] = parent_item[parent_link.parent_id_field]

                model_instance = self.resource_config.data_class.model_validate(value)
                model_instances.append(model_instance)
            except ValidationError as validation_error:
                return Response(convert_pydantic_validation_error_for_response(validation_error), 403, ())

        ids = await service.create(model_instances)
        return Response(ids, 201, ())

    async def update_item(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: Request,
    ) -> Response:
        """Processes an update item request"""

        await self.get_parent_items(request)
        payload = await request.get_json()

        if_match = request.get_header("If-Match")
        if self.resource_config.uses_etag and not if_match:
            raise SuperdeskApiError.preconditionRequiredError(
                "To edit a document its etag must be provided using the If-Match header"
            )

        if payload is None:
            raise SuperdeskApiError.badRequestError("Empty payload")

        try:
            await self.service.update(args.item_id, payload, if_match)
        except ValidationError as validation_error:
            return Response(convert_pydantic_validation_error_for_response(validation_error), 403, ())

        return Response({}, 200, ())

    async def delete_item(self, args: ItemRequestViewArgs, params: None, request: Request) -> Response:
        """Processes a delete item request"""

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

        await service.delete(original, if_match)
        return Response({}, 204, ())

    async def search_items(
        self,
        args: None,
        params: SearchRequest,
        request: Request,
    ) -> Response:
        """Processes a search request"""

        await self.get_parent_items(request)

        if len(self.endpoint_config.parent_links or []):
            if not isinstance(params.where, dict):
                if params.where is None:
                    params.where = {}
                elif isinstance(params.where, str):
                    params.where = cast(dict, json.loads(params.where))

            lookup = self.construct_parent_item_lookup(request)
            params.where.update(lookup)

        params.args = cast(SearchArgs, params.model_extra)
        cursor = await self.service.find(params)
        count = await cursor.count()

        response = RestGetResponse(
            _items=await cursor.to_list_raw(),
            _meta=dict(
                page=params.page,
                max_results=params.max_results,
                total=count,
            ),
        )

        status = 200
        headers = [("X-Total-Count", count)]
        response["_links"] = self._build_hateoas(params, count, request)
        response["_meta"] = dict(
            page=params.page,
            max_results=params.max_results,
            total=count,
        )
        if hasattr(cursor, "extra"):
            getattr(cursor, "extra")(response)

        return Response(response, status, headers)

    def _build_hateoas(self, req: SearchRequest, doc_count: Optional[int], request: Request) -> Dict[str, Any]:
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
