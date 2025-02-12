from typing import Annotated, cast
from enum import Enum, unique

from quart_babel import gettext
from pydantic_core import PydanticCustomError

from superdesk.core import get_app_config
from superdesk.core.resources import ResourceModelWithObjectId, Dataclass
from superdesk.core.resources.validators import validate_iunique_value_async, AsyncValidator

from .vocabularies import VocabulariesResourceModel


@unique
class FilterConditionOperator(str, Enum):
    IN = "in"
    NOT_IN = "nin"
    LIKE = "like"
    NOT_LIKE = "notlike"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    MATCH = "match"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    EXISTS = "exists"


class FilterConditionFieldParam(Dataclass):
    field: str
    operators: list[FilterConditionOperator]
    label: str | None = None
    values: list[str] | list[dict] | None = None
    value_field: str | None = None


DEFAULT_ALLOWED_FILTERS: list[str] = [
    "anpa_category",
    "urgency",
    "keywords",
    "priority",
    "slugline",
    "type",
    "source",
    "headline",
    "ednote",
    "body_html",
    "genre",
    "subject",
    "desk",
    "stage",
    "sms",
    "place",
    "ingest_provider",
    "embargo",
    "featuremedia",
    "anpa_take_key",
    "agendas",
]


async def validate_allowed_filter_fields(item: ResourceModelWithObjectId, field: str) -> None:
    allowed = DEFAULT_ALLOWED_FILTERS.copy() + cast(list[str], get_app_config("EXCLUDED_VOCABULARY_FIELDS", []))
    lookup = {"_id": {"$nin": allowed}, "type": "manageable"}
    async for vocabulary in await VocabulariesResourceModel.get_service().search(lookup):
        allowed.append(vocabulary.id)

    if field not in allowed:
        raise PydanticCustomError(
            "allowed",
            gettext(f"unallowed value {field}"),
        )


class FilterConditionsResource(ResourceModelWithObjectId):
    name: Annotated[str, validate_iunique_value_async("filter_conditions", "name")]
    field: Annotated[str, AsyncValidator(validate_allowed_filter_fields)]
    operator: FilterConditionOperator
    value: str
