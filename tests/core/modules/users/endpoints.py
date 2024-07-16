from typing import Optional

from pydantic import BaseModel

from superdesk.core.app import get_current_async_app
from superdesk.core.http.types import HTTPRequest, HTTPResponse, HTTPEndpointGroup, http_endpoint
from superdesk.errors import SuperdeskApiError


class RequestArgs(BaseModel):
    item_id: str


class RequestParams(BaseModel):
    resource: Optional[str] = None


endpoints = HTTPEndpointGroup()


@endpoints.endpoint(
    url="test_simple_route/<string:item_id>",
    methods=["GET"],
    name="test_simple_route|test",
)
async def test_simple_route(args: RequestArgs, params: RequestParams, request: HTTPRequest) -> HTTPResponse:
    item_id = args.item_id
    resource = params.resource or "users_async"
    app = get_current_async_app()

    item = await app.resources.get_resource_service(resource).find_by_id(item_id)
    if item is None:
        raise SuperdeskApiError.notFoundError("Item not found")
    return HTTPResponse(item.model_dump(by_alias=True, exclude_unset=True, mode="json"), 200, ())


@endpoints.endpoint(url="get_user_ids", methods=["GET"], name="get_user_ids|test")
async def get_user_ids(request: HTTPRequest) -> HTTPResponse:
    app = get_current_async_app()
    item_ids = []

    cursor = await app.resources.get_resource_service("users_async").search({})
    async for item in cursor:
        item_ids.append(item.id)

    return HTTPResponse({"ids": item_ids}, 200, ())


@http_endpoint("hello/world", methods=["GET"])
async def hello_world(request: HTTPRequest) -> HTTPResponse:
    return HTTPResponse({"hello": "world"}, 200, ())
