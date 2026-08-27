from typing import Annotated, Any

from pydantic import AfterValidator, AnyHttpUrl, BeforeValidator, Field, TypeAdapter
from pydantic_core import PydanticCustomError
from quart_babel import gettext

from superdesk.core.resources import ResourceModelWithObjectId
from superdesk.core.resources.validators import validate_not_empty

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
