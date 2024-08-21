# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import List, Optional, cast, Dict, Any, TypedDict, Type
import math

from dataclasses import dataclass
from pydantic import ValidationError
from eve.utils import querydef
from werkzeug.datastructures import MultiDict

from superdesk.core.app import get_current_async_app
from superdesk.errors import SuperdeskApiError

from ..web.types import HTTP_METHOD, Request, Response, RestGetResponse
from ..web.rest_endpoints import RestEndpoints, ItemRequestViewArgs

from .model import ResourceConfig, ResourceModel
from .cursor import SearchRequest, SearchArgs
from .validators import convert_pydantic_validation_error_for_response
from .utils import resource_uses_objectid_for_id


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


def get_id_url_type(data_class: type[ResourceModel]) -> str:
    """Get the URL param type for the ID field for route registration"""

    if resource_uses_objectid_for_id(data_class):
        return 'regex("[a-f0-9]{24}")'
    else:
        return 'regex("[\w,.:_-]+")'


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
        super().__init__(
            url=resource_config.name,
            name=resource_config.name,
            import_name=resource_config.__module__,
            resource_methods=endpoint_config.resource_methods,
            item_methods=endpoint_config.item_methods,
            id_param_type=endpoint_config.id_param_type or get_id_url_type(resource_config.data_class),
        )
        self.resource_config = resource_config
        self.endpoint_config = endpoint_config

    async def process_get_item_request(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: Request,
    ) -> Response:
        """Processes a get single item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        item = await service.find_by_id_raw(args.item_id)
        if not item:
            raise SuperdeskApiError.notFoundError(
                f"{self.resource_config.name} resource with ID '{args.item_id}' not found"
            )

        return Response(
            body=item,
            status_code=200,
            headers=(),
        )

    async def process_post_item_request(self, request: Request) -> Response:
        """Processes a create item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
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
                model_instance = self.resource_config.data_class.model_validate(value)
                model_instances.append(model_instance)
            except ValidationError as validation_error:
                return Response(convert_pydantic_validation_error_for_response(validation_error), 403, ())

        ids = await service.create(model_instances)
        return Response(ids, 201, ())

    async def process_patch_item_request(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: Request,
    ) -> Response:
        """Processes an update item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        payload = await request.get_json()

        if_match = request.get_header("If-Match")
        if self.resource_config.uses_etag and not if_match:
            raise SuperdeskApiError.preconditionRequiredError(
                "To edit a document its etag must be provided using the If-Match header"
            )

        if payload is None:
            raise SuperdeskApiError.badRequestError("Empty payload")

        try:
            await service.update(args.item_id, payload, if_match)
        except ValidationError as validation_error:
            return Response(convert_pydantic_validation_error_for_response(validation_error), 403, ())

        return Response({}, 200, ())

    async def process_delete_item_request(self, args: ItemRequestViewArgs, params: None, request: Request) -> Response:
        """Processes a delete item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
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

    async def process_get_request(
        self,
        args: None,
        params: SearchRequest,
        request: Request,
    ) -> Response:
        """Processes a search request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        params.args = cast(SearchArgs, params.model_extra)
        cursor = await service.find(params)
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
        response["_links"] = self._build_hateoas(self.resource_config.name, params, count, request)
        response["_meta"] = dict(
            page=params.page,
            max_results=params.max_results,
            total=count,
        )
        if hasattr(cursor, "extra"):
            getattr(cursor, "extra")(response)

        return Response(response, status, headers)

    def _build_hateoas(
        self, resource_name: str, req: SearchRequest, doc_count: Optional[int], request: Request
    ) -> Dict[str, Any]:
        links = {
            "parent": {
                "title": "home",
                "href": "/",
            },
            "self": {
                "title": resource_name,  # TODO: Get Resource Title,
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

        q = querydef(req.max_results, req.where, req.sort, None, req.page, other_params)

        if doc_count:
            links["self"]["href"] += q

        pagination_ink = links["self"]["href"].split("?")[0]
        if req.page * req.max_results >= (doc_count or 0):
            q = querydef(
                req.max_results,
                req.where,
                req.sort,
                None,
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
                    None,
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
                None,
                req.page - 1,
                other_params,
            )
            links["prev"] = {
                "title": "previous page",
                "href": f"{pagination_ink}{q}",
            }

        return links
