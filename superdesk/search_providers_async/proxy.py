# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from dataclasses import dataclass
import bson
import bson.errors
from typing import Annotated, Any, cast

from quart import abort, request

from apps.io.search_ingest import SearchIngestServiceAsync
from apps.search_providers.service import SearchProviderServiceAsync
from superdesk import get_resource_service
from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.resources import fields
from superdesk.core.resources.validators import validate_data_relation_async
from superdesk.types.search_providers import SearchProvider
from superdesk.utc import utcnow
from superdesk.utils import ListCursor
from superdesk.core.web import endpoint
from superdesk.core.types import Request, Response
from superdesk.users.services import current_user_has_item_privilege
from superdesk.search_providers_async import registered_search_providers


PROXY_ENDPOINT = "search_providers_proxy"


@dataclass
class SearchProviderProxyConfig:
    guid: str
    desk: Annotated[fields.ObjectId | None, validate_data_relation_async("desk")] = None
    repo: Annotated[fields.ObjectId | None, validate_data_relation_async("search_providers")] = None
    stage: Annotated[fields.ObjectId | None, validate_data_relation_async("stages")] = None
    fetch_endpoint: str | None = None
    search_provider: str | None = None
    _fetchable: bool = False


async def get_provider(provider_id: str | None = None) -> dict[str, Any] | str:
    """Get provider by ID or from request args."""
    if not provider_id:
        provider_id = request.args.get("repo")
    if provider_id is None:
        abort(400)
    # TODO-ASYNC [search_providers]: use the Async service
    search_providers_service = get_resource_service("search_providers")
    assert search_providers_service is not None
    search_providers_service = cast(SearchProviderServiceAsync, search_providers_service)
    provider = await search_providers_service.find_one_async(req=None, _id=provider_id)
    if not provider:
        abort(400)
    if provider.get("is_closed"):
        abort(400)
    if not current_user_has_item_privilege("search_providers", provider):
        abort(403)
    return provider


async def _get_service(provider: dict[str, Any] | str) -> str | SearchProvider:
    """Get the service instance for the provider."""
    if isinstance(provider, str):
        return provider if "," not in provider and provider else "search"

    provider_data = registered_search_providers[provider["search_provider"]]
    if provider_data.endpoint is not None:
        return provider_data.endpoint
    else:
        assert provider_data.provider_class is not None
        return provider_data.provider_class(provider)


async def _set_item_defaults(item: dict[str, Any], provider: dict[str, Any]) -> None:
    """Add default values to external items."""
    now = utcnow()
    item.setdefault("_id", item.get("guid") or bson.ObjectId())
    item.setdefault("_type", "externalsource")
    item.setdefault("type", "picture")
    item.setdefault("pubstatus", "usable")
    item.setdefault("firstcreated", now)
    item.setdefault("versioncreated", now)
    item.setdefault("fetch_endpoint", PROXY_ENDPOINT)
    item.setdefault("ingest_provider", str(provider["_id"]))


async def search_items(lookup: dict[str, Any], provider_id: str | None = None) -> ListCursor:
    """Search using provider."""
    # TODO-ASYNC [search_providers]: to be checked when search providers are async.
    provider = await get_provider(provider_id)
    service = await _get_service(provider)

    if isinstance(service, str):
        resource_service = get_resource_service(service)
        assert resource_service is not None
        resource_service = cast(SearchProviderServiceAsync, resource_service)
        return await resource_service.get_async(req=None, lookup=lookup)

    query = lookup.get("query", {})
    params = lookup.get("params", {})

    items = await service.find(query, params)

    if isinstance(items, list):
        items = ListCursor(items)

    for item in items:
        assert not isinstance(provider, str)
        await _set_item_defaults(item, provider)
    return items


@endpoint("/search_providers_proxy", methods=["GET", "POST"], auth=[required_privilege_rule("search_providers")])
async def search_providers_proxy(request: Request) -> Response:
    """Endpoint for search provider proxy operations."""
    if request.method == "GET":
        lookup = await request.get_json() or {}
        items = await search_items(lookup)
        return Response(items, 200)

    elif request.method == "POST":
        data = await request.get_json()
        if not isinstance(data, list):
            data = [data]

        provider = await get_provider()
        service = await _get_service(provider)

        if isinstance(service, str):
            resource_service = get_resource_service(service)
            assert resource_service is not None
            resource_service = cast(SearchProviderServiceAsync, resource_service)
            assert resource_service.is_async
            result = await resource_service.create_async(data)
        else:
            search_ingest_service = get_resource_service("search_ingest")
            assert search_ingest_service is not None
            search_ingest_service = cast(SearchIngestServiceAsync, search_ingest_service)
            # TODO-ASYNC[ingest-service]: to be checked
            result = await search_ingest_service.create(data)

        return Response(result, 201)
    else:
        return Response("bad request", 400)
