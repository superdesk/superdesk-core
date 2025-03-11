from superdesk.core.types import Request, Response, SearchRequest
from superdesk.core.resources import ResourceRestEndpoints


class ContentFilterRestEndpoints(ResourceRestEndpoints):
    async def search_items(
        self,
        args: None,
        params: SearchRequest,
        request: Request,
    ) -> Response:
        """Processes a search request

        Support URL param ``is_global`` directly without the ``where`` param
        """

        if request.get_url_arg("is_global"):
            self.update_where_filter(params, {"is_global": True})

        return await super().search_items(args, params, request)
