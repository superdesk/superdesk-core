from pydantic import BaseModel, field_validator
from quart_babel import gettext
from eve.utils import ParsedRequest
from bson import ObjectId

from superdesk.core import json
from superdesk.core.types import Request, Response
from superdesk.core.resources import fields
from superdesk.core.web import EndpointGroup
from superdesk.core.auth.privilege_rules import required_privilege_rule

from superdesk import get_resource_service
from superdesk.types import ContentFiltersResource
from superdesk.errors import SuperdeskApiError
from superdesk.publish_async.utils import (
    content_filter_to_elastic_query,
    item_matches_content_filter,
    get_available_filter_params,
)
from superdesk.publish_async.publish_cache import PublishCache


publish_endpoints = EndpointGroup("publish", __name__)


@publish_endpoints.endpoint("filter_conditions/parameters", "filter_conditions_parameters", methods=["GET"])
async def content_params_endpoint() -> Response:
    params = await get_available_filter_params()
    return Response(
        {
            "_status": "OK",
            "_meta": {"total": len(params)},
            "_items": [param.to_dict() for param in params],
        }
    )


class ContentFilterTestArgs(BaseModel):
    filter_id: fields.ObjectId | None = None
    article_id: str | None = None
    return_matching: bool = False
    filter: ContentFiltersResource | None = None

    @field_validator("filter", mode="before")
    def parse_filter(cls, value: ContentFiltersResource | dict | None) -> ContentFiltersResource | dict | None:
        if isinstance(value, dict):
            # If a filter is provided, use mock ID and name (as they're required by the resource model)
            value.setdefault("_id", str(ObjectId()))
            value.setdefault("name", "<content_filter_test>")
        return value


@publish_endpoints.endpoint(
    "content_filters/test", "content_filter_tests", methods=["POST"], auth=[required_privilege_rule("content_filters")]
)
async def content_filter_test_endpoint(request: Request) -> Response:
    args = ContentFilterTestArgs.model_validate_json(await request.get_data())
    content_filter_service = ContentFiltersResource.get_service()
    archive_service = get_resource_service("archive")
    ingest_service = get_resource_service("ingest")
    await PublishCache.init()

    try:
        planning_service = get_resource_service("planning")
    except KeyError:
        planning_service = None

    result: dict = {}
    content_filter: ContentFiltersResource | None = None
    if args.filter_id:
        content_filter = await content_filter_service.find_by_id(args.filter_id)
    elif args.filter:
        content_filter = args.filter

    if not content_filter:
        raise SuperdeskApiError.badRequestError(gettext("Content filter not found"))

    if args.article_id:
        article: dict | None = await archive_service.find_one_async(req=None, _id=args.article_id)
        if not article and planning_service:
            article = await planning_service.find_one_async(req=None, _id=args.article_id)
        if not article:
            article = await ingest_service.find_one_async(req=None, _id=args.article_id)
        if not article:
            raise SuperdeskApiError.badRequestError(gettext("Article not found"))

        print("Testing against single article")
        print(article)
        print(content_filter)

        try:
            result["match_results"] = item_matches_content_filter(article, content_filter)
        except Exception as ex:
            raise SuperdeskApiError.badRequestError(gettext(f"Error in testing article: {ex}"))
    else:
        try:
            query = {
                "query": {
                    "filtered": {"query": await content_filter_to_elastic_query(content_filter, args.return_matching)}
                },
                "sort": [{"versioncreated": "desc"}],
                "size": 200,
            }
            req = ParsedRequest()
            req.args = {"source": json.dumps(query)}
            cursor = await get_resource_service("archive").get_async(req=req, lookup=None)
            result["match_results"] = await cursor.to_list()
        except Exception as ex:
            raise SuperdeskApiError.badRequestError(gettext(f"Error in testing archive: {ex}"))

    result["_status"] = "OK"
    return Response(result, 201)
