from typing import List, Dict, Callable, Set
import warnings
import superdesk

from flask import current_app as app, request
from flask_babel import _
from datetime import timedelta
from superdesk.utils import ListCursor
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError


SETTING_ENABLED = "ARCHIVE_AUTOCOMPLETE"
SETTING_DAYS = "ARCHIVE_AUTOCOMPLETE_DAYS"
SETTING_HOURS = "ARCHIVE_AUTOCOMPLETE_HOURS"
SETTING_LIMIT = "ARCHIVE_AUTOCOMPLETE_LIMIT"


AutocompleteSuggestionProvider = Callable[[str, str], Set[str]]
_registered_autocomplete_resources: Dict[str, AutocompleteSuggestionProvider] = {}


def register_autocomplete_suggestion_provider(resource: str, provider: AutocompleteSuggestionProvider):
    _registered_autocomplete_resources[resource] = provider


class AutocompleteResource(superdesk.Resource):
    item_methods = []
    resource_methods = ["GET"]
    schema = {
        "value": {"type": "string"},
    }


class AutocompleteService(superdesk.Service):
    def get(self, req, lookup):
        resources: List[str] = (
            _registered_autocomplete_resources.keys()
            if not request.args.get("resources")
            else request.args.get("resources").split(",")
        )
        field: str = request.args.get("field", "slugline")
        language: str = request.args.get("language", app.config.get("DEFAULT_LANGUAGE", "en"))

        all_suggestions: Set[str] = set()
        for resource in resources:
            get_suggestions = _registered_autocomplete_resources.get(resource)
            if not get_suggestions:
                raise SuperdeskApiError(
                    _(f"Autocomplete suggestion for resource type '{resource}' not registered"), 404
                )

            suggestions = get_suggestions(field, language)
            if suggestions:
                all_suggestions = all_suggestions.union(suggestions)

        return ListCursor([{"value": suggestion} for suggestion in sorted(all_suggestions)])


def get_archive_suggestions(field: str, language: str) -> Set[str]:
    if not app.config.get(SETTING_ENABLED):
        raise SuperdeskApiError(_("Archive autocomplete is not enabled"), 404)

    field_mapping = {"slugline": "slugline.keyword"}

    if field not in field_mapping:
        raise SuperdeskApiError(_("Field %(field)s is not allowed", field=field), 400)

    versioncreated_min = (
        utcnow()
        - timedelta(
            days=app.config[SETTING_DAYS],
            hours=app.config[SETTING_HOURS],
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
                    "size": app.config[SETTING_LIMIT],
                    "order": {"_key": "asc"},
                },
            },
        },
    }
    res = app.data.elastic.search(query, "archive", params={"size": 0})
    return set([bucket["key"] for bucket in res.hits["aggregations"]["values"]["buckets"]])


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
