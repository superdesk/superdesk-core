from typing import Callable, Awaitable
from inspect import isawaitable
import warnings
import superdesk

from quart_babel import gettext as _
from datetime import timedelta

from superdesk.core import get_current_app, get_config, get_current_async_app
from superdesk.eve_async import AsyncBaseService, AsyncListCursor
from superdesk.types import ArchiveResourceModel
from superdesk.flask import request
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError


SETTING_ENABLED = "ARCHIVE_AUTOCOMPLETE"
SETTING_DAYS = "ARCHIVE_AUTOCOMPLETE_DAYS"
SETTING_HOURS = "ARCHIVE_AUTOCOMPLETE_HOURS"
SETTING_LIMIT = "ARCHIVE_AUTOCOMPLETE_LIMIT"


AutocompleteSuggestionProvider = Callable[[str, str], dict[str, int]] | Callable[[str, str], Awaitable[dict[str, int]]]
_registered_autocomplete_resources: dict[str, AutocompleteSuggestionProvider] = {}


def register_autocomplete_suggestion_provider(resource: str, provider: AutocompleteSuggestionProvider):
    _registered_autocomplete_resources[resource] = provider


class AutocompleteResource(superdesk.Resource):
    item_methods = []
    resource_methods = ["GET"]
    schema = {
        "value": {"type": "string"},
        "count": {"type": "integer"},
    }


class AutocompleteService(AsyncBaseService):
    async def get_async(self, req, lookup):
        resources: list[str] = (
            _registered_autocomplete_resources.keys()
            if not request.args.get("resources")
            else request.args.get("resources").split(",")
        )
        field: str = request.args.get("field", "slugline")
        language: str = request.args.get("language", get_config(str, "DEFAULT_LANGUAGE"))

        all_suggestions: dict[str, int] = {}
        for resource in resources:
            get_suggestions = _registered_autocomplete_resources.get(resource)
            if not get_suggestions:
                raise SuperdeskApiError(
                    _(f"Autocomplete suggestion for resource type '{resource}' not registered"), 404
                )

            suggestions = get_suggestions(field, language)
            if isawaitable(suggestions):
                suggestions = await suggestions
            for key, count in suggestions.items():
                all_suggestions.setdefault(key, 0)
                all_suggestions[key] += count

        return AsyncListCursor(
            [{"value": key, "count": all_suggestions[key]} for key in sorted(all_suggestions.keys())]
        )


async def get_archive_suggestions(field: str, language: str) -> dict[str, int]:
    if not get_config(bool, SETTING_ENABLED):
        raise SuperdeskApiError(_("Archive autocomplete is not enabled"), 404)

    field_mapping = {"slugline": "slugline.keyword"}

    if field not in field_mapping:
        raise SuperdeskApiError(_("Field %(field)s is not allowed", field=field), 400)

    versioncreated_min = (
        utcnow()
        - timedelta(
            days=get_config(int, SETTING_DAYS),
            hours=get_config(int, SETTING_HOURS),
        )
    ).replace(
        microsecond=0
    )  # avoid different microsecond each time so elastic has 1s to cache

    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"state": "published"}},
                    {"term": {"language": language}},
                    {"range": {"versioncreated": {"gte": versioncreated_min}}},
                ],
            },
        },
        "aggs": {
            "values": {
                "terms": {
                    "field": field_mapping[field],
                    "size": get_config(int, SETTING_LIMIT),
                    "order": {"_key": "asc"},
                },
            },
        },
        "size": 0,
    }

    async_app = get_current_async_app()
    index = async_app.elastic.get_elastic_index_name("archive")
    elastic = ArchiveResourceModel.get_service().elastic
    res = await elastic.search(query, [index])
    return {bucket["key"]: bucket["doc_count"] for bucket in res["aggregations"]["values"]["buckets"]}


def init_app(_app) -> None:
    _app.client_config.update({"archive_autocomplete": _app.config.get(SETTING_ENABLED, False)})

    if _app.config.get(SETTING_ENABLED) and not _app.config.get(SETTING_HOURS) and not _app.config.get(SETTING_DAYS):
        warnings.warn(
            "{} is enabled but both {} and {} are not set.".format(
                SETTING_ENABLED,
                SETTING_HOURS,
                SETTING_DAYS,
            )
        )

    superdesk.register_resource("archive_autocomplete", AutocompleteResource, AutocompleteService, _app=_app)
    register_autocomplete_suggestion_provider("archive", get_archive_suggestions)
