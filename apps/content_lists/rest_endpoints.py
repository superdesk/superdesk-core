from bson import ObjectId

from superdesk.core.types import Request, Response
from superdesk.core.web import Endpoint
from superdesk.core.resources import ResourceRestEndpoints


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
        result = await self.service.bulk_update(list_id, data)
        return Response(body=result.to_dict(), status_code=200)
