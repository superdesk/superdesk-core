# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import List, Optional, cast, Dict, Any
from datetime import datetime
import math

from pytz import utc
from pydantic import BaseModel, ValidationError
from eve.utils import querydef
from werkzeug.datastructures import MultiDict

from superdesk.metadata.item import GUID_NEWSML
from superdesk.metadata.utils import generate_guid
from superdesk.core.app import get_current_async_app
from superdesk.errors import SuperdeskApiError

from ..resources.model import ResourceModelConfig
from .types import HTTPEndpoint, HTTPEndpointGroup, HTTP_METHOD, HTTPRequest, HTTPResponse, RestGetResponse
from ..resources.cursor import SearchRequest, SearchArgs
from ..resources.validators import convert_pydantic_validation_error_for_response


class ItemRequestViewArgs(BaseModel):
    item_id: str


class ResourceEndpoints(HTTPEndpointGroup):
    """Custom HTTPEndpointGroup for REST resources"""

    #: The config for the resource to use
    resource_config: ResourceModelConfig

    #: Optional list of resource level methods, defaults to ["GET", "POST"]
    resource_methods: List[HTTP_METHOD]

    #: Optional list of item level methods, defaults to ["GET", "PATCH", "DELETE"]
    item_methods: List[HTTP_METHOD]

    def __init__(
        self,
        resource_config: ResourceModelConfig,
        resource_methods: Optional[List[HTTP_METHOD]] = None,
        item_methods: Optional[List[HTTP_METHOD]] = None,
    ):
        super().__init__()
        self.resource_config = resource_config
        self.resource_methods = resource_methods or ["GET", "POST"]
        self.item_methods = item_methods or ["GET", "PATCH", "DELETE"]

        if "GET" in self.resource_methods:
            self.endpoints.append(
                HTTPEndpoint(
                    url=self.resource_config.name,
                    name=f"{self.resource_config.name}|resource_get",
                    func=self.process_get_request,
                    methods=["GET"],
                )
            )

        if "POST" in self.resource_methods:
            self.endpoints.append(
                HTTPEndpoint(
                    url=self.resource_config.name,
                    name=f"{self.resource_config.name}|resource_post",
                    func=self.process_post_item_request,
                    methods=["POST"],
                )
            )

        item_url = f"{self.resource_config.name}/<string:item_id>"
        if "GET" in self.item_methods:
            self.endpoints.append(
                HTTPEndpoint(
                    url=item_url,
                    name=f"{self.resource_config.name}|item_get",
                    func=self.process_get_item_request,
                    methods=["GET"],
                )
            )

        if "PATCH" in self.item_methods:
            self.endpoints.append(
                HTTPEndpoint(
                    url=item_url,
                    name=f"{self.resource_config.name}|item_patch",
                    func=self.process_patch_item_request,
                    methods=["PATCH"],
                )
            )

        if "DELETE" in self.item_methods:
            self.endpoints.append(
                HTTPEndpoint(
                    url=item_url,
                    name=f"{self.resource_config.name}|item_delete",
                    func=self.process_delete_item_request,
                    methods=["DELETE"],
                )
            )

    async def process_get_item_request(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: HTTPRequest,
    ) -> HTTPResponse:
        """Processes a get single item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        item = await service.find_by_id(args.item_id)
        if not item:
            raise SuperdeskApiError.notFoundError(
                f"{self.resource_config.name} resource with ID '{args.item_id}' not found"
            )

        return HTTPResponse(
            body=item.model_dump(by_alias=True, exclude_unset=True, mode="json"), status_code=200, headers=()
        )

    async def process_post_item_request(self, request: HTTPRequest) -> HTTPResponse:
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
                value.setdefault("_id", generate_guid(type=GUID_NEWSML))
                model_instance = self.resource_config.data_class.model_validate(value)
                model_instances.append(model_instance)
            except ValidationError as validation_error:
                return HTTPResponse(convert_pydantic_validation_error_for_response(validation_error), 403, ())

        ids = await service.create(model_instances)
        return HTTPResponse(ids, 201, ())

    async def process_patch_item_request(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: HTTPRequest,
    ) -> HTTPResponse:
        """Processes an update item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        payload = await request.get_json()

        if payload is None:
            raise SuperdeskApiError.badRequestError("Empty payload")

        try:
            await service.update(args.item_id, payload)
        except ValidationError as validation_error:
            return HTTPResponse(convert_pydantic_validation_error_for_response(validation_error), 403, ())

        return HTTPResponse({}, 200, ())

    async def process_delete_item_request(
        self, args: ItemRequestViewArgs, params: None, request: HTTPRequest
    ) -> HTTPResponse:
        """Processes a delete item request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        original = await service.find_by_id(args.item_id)

        if original:
            await service.delete({"_id": original.id})

        return HTTPResponse({}, 204, ())

    async def process_get_request(
        self,
        args: None,
        params: SearchRequest,
        request: HTTPRequest,
    ) -> HTTPResponse:
        """Processes a search request"""

        service = get_current_async_app().resources.get_resource_service(self.resource_config.name)
        params.args = cast(SearchArgs, params.model_extra)
        cursor = await service.find(params)
        count = await cursor.count()

        response = RestGetResponse(
            _items=[],
            _meta=dict(
                page=params.page,
                max_results=params.max_results,
                total=count,
            ),
        )
        epoch = datetime(1970, 1, 1, tzinfo=utc)
        last_update = datetime(1970, 1, 1, tzinfo=utc)

        async for item in cursor:
            if item.updated > last_update:
                last_update = item.updated
            response["_items"].append(item.model_dump(by_alias=True, exclude_unset=True, mode="json"))

        last_modified = last_update if last_update > epoch else None
        status = 200
        etag = None
        headers = [("X-Total-Count", count)]

        response["_links"] = self._build_hateoas(self.resource_config.name, params, count, request)
        response["_meta"] = dict(
            page=params.page,
            max_results=params.max_results,
            total=count,
        )
        if hasattr(cursor, "extra"):
            getattr(cursor, "extra")(response)

        return HTTPResponse(response, status, headers)

    def _build_hateoas(
        self, resource_name: str, req: SearchRequest, doc_count: Optional[int], request: HTTPRequest
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
