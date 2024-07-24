# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import List, Optional

from pydantic import BaseModel

from .types import Endpoint, EndpointGroup, HTTP_METHOD, Request, Response
from ..resources.cursor import SearchRequest


class ItemRequestViewArgs(BaseModel):
    item_id: str


class RestEndpoints(EndpointGroup):
    """Custom EndpointGroup for REST resources"""

    #: The URL for this resource
    url: str

    #: The list of HTTP methods for the resource endpoints
    resource_methods: List[HTTP_METHOD]

    #: The list of HTTP methods for the resource item endpoints
    item_methods: List[HTTP_METHOD]

    #: Optionally set the route param type for the ID, defaults to ``string``
    id_param_type: str

    def __init__(
        self,
        url: str,
        name: str,
        import_name: Optional[str] = None,
        resource_methods: Optional[List[HTTP_METHOD]] = None,
        item_methods: Optional[List[HTTP_METHOD]] = None,
        id_param_type: Optional[str] = None,
    ):
        super().__init__(name, import_name or __name__)
        self.url = url
        self.resource_methods = resource_methods or ["GET", "POST"]
        self.item_methods = item_methods or ["GET", "PATCH", "DELETE"]
        self.id_param_type = id_param_type or "string"

        if "GET" in self.resource_methods:
            self.endpoints.append(
                Endpoint(
                    url=self.url,
                    name=f"{self.name}|resource_get",
                    func=self.process_get_request,
                    methods=["GET"],
                )
            )

        if "POST" in self.resource_methods:
            self.endpoints.append(
                Endpoint(
                    url=self.url,
                    name=f"{self.name}|resource_post",
                    func=self.process_post_item_request,
                    methods=["POST"],
                )
            )

        item_url = f"{self.url}/<{self.id_param_type}:item_id>"
        if "GET" in self.item_methods:
            self.endpoints.append(
                Endpoint(
                    url=item_url,
                    name=f"{self.name}|item_get",
                    func=self.process_get_item_request,
                    methods=["GET"],
                )
            )

        if "PATCH" in self.item_methods:
            self.endpoints.append(
                Endpoint(
                    url=item_url,
                    name=f"{self.name}|item_patch",
                    func=self.process_patch_item_request,
                    methods=["PATCH"],
                )
            )

        if "DELETE" in self.item_methods:
            self.endpoints.append(
                Endpoint(
                    url=item_url,
                    name=f"{self.name}|item_delete",
                    func=self.process_delete_item_request,
                    methods=["DELETE"],
                )
            )

    async def process_get_item_request(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: Request,
    ) -> Response:
        """Processes a get single item request"""

        raise NotImplementedError()

    async def process_post_item_request(self, request: Request) -> Response:
        """Processes a create item request"""

        raise NotImplementedError()

    async def process_patch_item_request(
        self,
        args: ItemRequestViewArgs,
        params: None,
        request: Request,
    ) -> Response:
        """Processes an update item request"""

        raise NotImplementedError()

    async def process_delete_item_request(self, args: ItemRequestViewArgs, params: None, request: Request) -> Response:
        """Processes a delete item request"""

        raise NotImplementedError()

    async def process_get_request(
        self,
        args: None,
        params: SearchRequest,
        request: Request,
    ) -> Response:
        """Processes a search request"""

        raise NotImplementedError()
