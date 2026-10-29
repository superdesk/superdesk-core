from datetime import datetime
import re
from typing import Any

from eve_elastic import Elastic
from eve_elastic.elastic import parse_date
from quart import current_app

from superdesk.datalayer import SuperdeskDataLayer
from superdesk.eve_async import ElasticAsync


def parse_datetimes(value: Any, schema: dict) -> Any:
    """Restore datetime types using resource schemas, never string contents."""
    if isinstance(value, str) and (
        schema.get("type") == "datetime" or (schema.get("mapping") or {}).get("type") == "date"
    ):
        # Elasticsearch date mappings also represent date-only fields.
        if schema.get("type") != "datetime" and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return value
        return parse_date(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, dict):
        fields = {
            **{key: {"mapping": field} for key, field in (schema.get("mapping") or {}).get("properties", {}).items()},
            **schema.get("schema", {}),
        }
        return {
            key: parse_datetimes(item, fields.get(key, schema.get("valuesrules", {}))) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [parse_datetimes(item, schema.get("schema", schema)) for item in value]
    return value


def get_schema(resource: str) -> dict:
    return {
        "type": "dict",
        "schema": {
            **current_app.config.get("_PRODAPI_RESPONSE_SCHEMAS", {}).get(resource, {}),
            **current_app.config["DOMAIN"].get(resource, {}).get("schema", {}),
        },
    }


class ProdApiElastic(Elastic):
    def get_hits_docs(self, hits, resource):
        return [parse_datetimes(doc, get_schema(resource)) for doc in super().get_hits_docs(hits, resource)]


class ProdApiElasticAsync(ProdApiElastic, ElasticAsync):
    pass


class ProdApiDataLayer(SuperdeskDataLayer):
    elastic_class = ProdApiElastic
    elastic_async_class = ProdApiElasticAsync

    async def find_one_async(self, resource, req, check_auth_value=True, force_auth_field_projection=False, **lookup):
        item = await super().find_one_async(resource, req, check_auth_value, force_auth_field_projection, **lookup)
        return parse_datetimes(item, get_schema(resource))
