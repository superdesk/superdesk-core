from typing import cast

from superdesk.core import json
from superdesk.core.types import Request, Response, SearchRequest, RestGetResponse, RestResponseMeta
from superdesk.core.resources import ResourceRestEndpoints, ItemRequestUrlArgs
from superdesk.core.web import ItemRequestViewArgs

from superdesk.types import SubscribersResource
from .utils import _get_subscribers_by_filter_condition


class SubscriberRestEndpoints(ResourceRestEndpoints):
    hide_fields = {"secret_token", "password", "apiKey", "access_key_id", "secret_access_key"}

    async def get_item(
        self,
        args: ItemRequestViewArgs,
        params: ItemRequestUrlArgs,
        request: Request,
    ) -> Response:
        """Processes a get single item request"""
        response = await super().get_item(args, params, request)

        body = response.body.to_dict() if isinstance(response.body, SubscribersResource) else cast(dict, response.body)
        self._hide_config_fields(body, self.hide_fields)
        response.body = body
        return response

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
            for subscriber in subscribers["selected_subscribers"]:
                self._hide_config_fields(subscriber, self.hide_fields)
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

        response = await super().search_items(args, params, request)

        for doc in cast(RestGetResponse, response.body)["_items"]:
            self._hide_config_fields(doc, self.hide_fields)

        return response

    def _hide_config_fields(self, doc: dict, fields: set[str]) -> None:
        for destination in doc.get("destinations") or []:
            if not destination.get("config"):
                continue
            destination["config"] = {key: value for key, value in destination["config"] if key not in fields}
