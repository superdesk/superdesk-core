from typing import List, Dict, Callable, cast
import warnings
import superdesk

from quart_babel import gettext as _
from datetime import timedelta

from superdesk.core import get_current_app, get_app_config
from superdesk.flask import request
from superdesk.utils import ListCursor
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError


SETTING_ENABLED = "ARCHIVE_AUTOCOMPLETE"
SETTING_DAYS = "ARCHIVE_AUTOCOMPLETE_DAYS"
SETTING_HOURS = "ARCHIVE_AUTOCOMPLETE_HOURS"
SETTING_LIMIT = "ARCHIVE_AUTOCOMPLETE_LIMIT"


AutocompleteSuggestionProvider = Callable[[str, str], Dict[str, int]]
_registered_autocomplete_resources: Dict[str, AutocompleteSuggestionProvider] = {}


def register_autocomplete_suggestion_provider(resource: str, provider: AutocompleteSuggestionProvider):
    _registered_autocomplete_resources[resource] = provider


class AutocompleteResource(superdesk.Resource):
    item_methods = []
    resource_methods = ["GET"]
    schema = {
        "value": {"type": "string"},
        "count": {"type": "integer"},
    }


class AutocompleteService(superdesk.Service):
    def get(self, req, lookup):
        resources: List[str] = (
            _registered_autocomplete_resources.keys()
            if not request.args.get("resources")
            else request.args.get("resources").split(",")
        )
        field: str = request.args.get("field", "slugline")
        language: str = request.args.get("language", get_app_config("DEFAULT_LANGUAGE", "en"))

        all_suggestions: Dict[str, int] = {}
        for resource in resources:
            get_suggestions = _registered_autocomplete_resources.get(resource)
            if not get_suggestions:
                raise SuperdeskApiError(
                    _(f"Autocomplete suggestion for resource type '{resource}' not registered"), 404
                )

            for key, count in get_suggestions(field, language).items():
                all_suggestions.setdefault(key, 0)
                all_suggestions[key] += count

        return ListCursor([{"value": key, "count": all_suggestions[key]} for key in sorted(all_suggestions.keys())])


def get_archive_suggestions(field: str, language: str) -> Dict[str, int]:
    if not get_app_config(SETTING_ENABLED):
        raise SuperdeskApiError(_("Archive autocomplete is not enabled"), 404)

    field_mapping = {"slugline": "slugline.keyword"}

    if field not in field_mapping:
        raise SuperdeskApiError(_("Field %(field)s is not allowed", field=field), 400)

    versioncreated_min = (
        utcnow()
        - timedelta(
            days=cast(int, get_app_config(SETTING_DAYS)),
            hours=cast(int, get_app_config(SETTING_HOURS)),
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
                    "size": get_app_config(SETTING_LIMIT),
                    "order": {"_key": "asc"},
                },
            },
        },
    }
    res = get_current_app().data.elastic.search(query, "archive", params={"size": 0})
    return {bucket["key"]: bucket["doc_count"] for bucket in res.hits["aggregations"]["values"]["buckets"]}


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
