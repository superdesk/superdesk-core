from typing import TYPE_CHECKING, NamedTuple

from quart_babel import gettext, lazy_gettext
from quart_babel.speaklater import LazyString

from superdesk.errors import AlreadyExistsError, SuperdeskApiError

from .base import AIProviderClient
from .openai_compatible import OpenAICompatibleClient

if TYPE_CHECKING:
    from ..models import AIProvider


class AIProviderTypeData(NamedTuple):
    name: str
    client_class: type[AIProviderClient]
    label: str | LazyString


registered_provider_types: dict[str, AIProviderTypeData] = {}

#: Names of the registered provider types, used to validate ``AIProvider.provider_type``
allowed_provider_types: list[str] = []


def register_provider_type(
    name: str,
    client_class: type[AIProviderClient],
    label: str | LazyString | None = None,
) -> None:
    """Register an AI provider type, making it available to ``ai_providers``

    :param name: Name of the provider type, unique in the system and stored on every provider
    :param client_class: The client used to talk to providers of this type
    :param label: Optional human readable name, falls back to ``name``
    :raises AlreadyExistsError: If a provider type with the same name is already registered
    """

    if name in registered_provider_types:
        raise AlreadyExistsError(f"An AI provider type with name: {name} already exists")

    registered_provider_types[name] = AIProviderTypeData(name, client_class, label or name)
    allowed_provider_types.append(name)


def get_provider_type(name: str) -> AIProviderTypeData | None:
    """Return the registration for a provider type name, or ``None`` when it is not registered"""

    return registered_provider_types.get(name)


def get_client(provider: "AIProvider") -> AIProviderClient:
    """Build the client used to talk to the given provider

    :raises SuperdeskApiError.badRequestError: If the provider holds a type that is not registered,
        which happens when the module that registered it is no longer installed
    """

    provider_type = get_provider_type(provider.provider_type)
    if provider_type is None:
        raise SuperdeskApiError.badRequestError(
            gettext("Unknown AI provider type '{provider_type}'").format(provider_type=provider.provider_type)
        )

    return provider_type.client_class(
        base_url=provider.base_url,
        api_key=provider.api_key,
        config=provider.config,
    )


register_provider_type("openai_compatible", OpenAICompatibleClient, lazy_gettext("OpenAI compatible"))
