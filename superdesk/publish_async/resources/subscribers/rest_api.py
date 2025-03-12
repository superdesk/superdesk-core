from typing import cast

from superdesk.core import json
from superdesk.core.types import Request, Response, SearchRequest, RestGetResponse, RestResponseMeta
from superdesk.core.resources import ResourceRestEndpoints

from .utils import _get_subscribers_by_filter_condition


class SubscriberRestEndpoints(ResourceRestEndpoints):
    async def search_items(
        self,
        args: None,
        params: SearchRequest,
        request: Request,
    ) -> Response:
        """Processes a search request"""

        filter_condition_str = request.get_url_arg("filter_condition")
        if filter_condition_str:
            filter_condition = json.loads(filter_condition_str)
            subscribers = await _get_subscribers_by_filter_condition(filter_condition)
            return Response(
                RestGetResponse(
                    _items=[cast(dict, subscribers)],
                    _meta=RestResponseMeta(
                        page=1,
                        max_results=params.max_results,
                        total=1,
                    ),
                )
            )

        return await super().search_items(args, params, request)
