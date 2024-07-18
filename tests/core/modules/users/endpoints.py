from typing import Optional

from pydantic import BaseModel

from superdesk.core.app import get_current_async_app
from superdesk.core.web import Request, Response, EndpointGroup, endpoint
from superdesk.errors import SuperdeskApiError


class RequestArgs(BaseModel):
    item_id: str


class RequestParams(BaseModel):
    resource: Optional[str] = None


endpoints = EndpointGroup()


@endpoints.endpoint(
    url="test_simple_route/<string:item_id>",
    methods=["GET"],
    name="test_simple_route|test",
)
async def test_simple_route(args: RequestArgs, params: RequestParams, request: Request) -> Response:
    item_id = args.item_id
    resource = params.resource or "users_async"
    app = get_current_async_app()

    item = await app.resources.get_resource_service(resource).find_by_id(item_id)
    if item is None:
        raise SuperdeskApiError.notFoundError("Item not found")
    return Response(item.model_dump(by_alias=True, exclude_unset=True, mode="json"), 200, ())


@endpoints.endpoint(url="get_user_ids", methods=["GET"], name="get_user_ids|test")
async def get_user_ids(request: Request) -> Response:
    app = get_current_async_app()
    item_ids = []

    cursor = await app.resources.get_resource_service("users_async").search({})
    async for item in cursor:
        item_ids.append(item.id)

    return Response({"ids": item_ids}, 200, ())


@endpoint("hello/world", methods=["GET"])
async def hello_world(request: Request) -> Response:
    return Response({"hello": "world"}, 200, ())
