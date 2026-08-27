import enum
from typing import Annotated, Any

from pydantic import AfterValidator, AnyHttpUrl, BeforeValidator, Field, TypeAdapter
from pydantic_core import PydanticCustomError
from quart_babel import gettext

from superdesk.core.resources import Dataclass, ResourceModelWithObjectId, dataclass, fields
from superdesk.core.resources.validators import (
    validate_data_relation_async,
    validate_maxlength,
    validate_minlength,
    validate_not_empty,
)

from .providers import allowed_provider_types

_http_url_adapter: TypeAdapter = TypeAdapter(AnyHttpUrl)

# Validates as an HTTP(S) URL and stores it without a trailing slash. Provider clients append
# their paths with a leading slash, so a stored trailing slash would produce a double slash in
# every request URL. Kept a plain ``str`` so it stays serializable for MongoDB storage.
BaseUrlStr = Annotated[str, BeforeValidator(lambda value: str(_http_url_adapter.validate_python(value)).rstrip("/"))]


def validate_provider_type() -> AfterValidator:
    """Validates that the value is the name of a registered AI provider type"""

    def _validate_provider_type(value: str) -> str:
        if value not in allowed_provider_types:
            raise PydanticCustomError(
                "provider_type",
                gettext("Unknown AI provider type '{provider_type}'"),
                {"provider_type": value},
            )

        return value

    return AfterValidator(_validate_provider_type)


class AIProvider(ResourceModelWithObjectId):
    name: Annotated[str, validate_not_empty()]
    provider_type: Annotated[str, validate_provider_type()]
    base_url: BaseUrlStr
    api_key: str | None = None
    default_model: str | None = None
    is_default: bool = False
    active: bool = True

    #: Type specific extras, such as the headers a gateway requires
    config: dict[str, Any] = Field(default_factory=dict)
    label: str | None = None


class AIActionType(str, enum.Enum):
    SUGGESTION = "suggestion"
    SUMMARY = "summary"
    REWRITE = "rewrite"
    TRANSLATION = "translation"


@dataclass
class AIActionParameters(Dataclass):
    temperature: float = 0.7

    #: Replaces the system prompt built from the action type, leaving the instructions that carry
    #: the answer format in place
    system_prompt: str | None = None


class AIAction(ResourceModelWithObjectId):
    name: Annotated[str, validate_not_empty()]
    action_type: AIActionType
    active: bool = True

    #: Names of the item fields whose text is sent to the provider
    input_fields: Annotated[list[str], validate_minlength(1)]

    #: Name of the item field the suggestions are written back to by the client
    output_field: Annotated[str, validate_not_empty()]

    max_characters: int | None = None
    suggestions_count: Annotated[int, validate_minlength(1), validate_maxlength(10)] = 3

    #: Content profiles the action is offered for, an empty list means every profile
    content_profiles: list[str] = Field(default_factory=list)

    provider: Annotated[fields.ObjectId, validate_data_relation_async("ai_providers")]

    #: Model to run the action with, falls back to the provider's ``default_model``
    model: str | None = None

    parameters: AIActionParameters = Field(default_factory=AIActionParameters)
