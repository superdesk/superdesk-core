from bson import ObjectId

from superdesk.core.types import Request, Response, RestGetResponse
from superdesk.core.web import Endpoint
from superdesk.core.resources import ResourceRestEndpoints

from .article_content import enrich_fetched_item, enrich_fetched_response


class ContentListItemsEndpoints(ResourceRestEndpoints):
    def add_endpoints(self):
        super().add_endpoints()
        self.endpoints.append(
            Endpoint(
                url=self.get_resource_url(),
                name="content_list_items_bulk_patch",
                func=self.bulk_patch_items,
                methods=["PATCH"],
                parent=self,
            )
        )

    async def bulk_patch_items(self, request: Request) -> Response:
        list_id = ObjectId(request.get_view_args("list_id"))
        data = await request.get_json()
        result = await self.service.bulk_patch(list_id, data)
        return Response(body=result.to_dict(), status_code=200)

    async def on_fetched(self, request: Request, doc: RestGetResponse) -> None:
        await enrich_fetched_response(doc)

    async def on_fetched_item(self, request: Request, doc: dict) -> None:
        await enrich_fetched_item(doc)
