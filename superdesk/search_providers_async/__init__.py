from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.types import Response
from superdesk.core.web import endpoint
from superdesk.errors import AlreadyExistsError
from superdesk.text_utils import get_text as _
from superdesk.types.search_providers import SearchProviderData, SearchProvider


registered_search_providers: dict[str, SearchProviderData] = {}
allowed_search_providers: list[str] = []


def register_search_provider(
    name: str,
    fetch_endpoint: str | None = None,
    provider_class: type[SearchProvider] | None = None,
    label: str | None = None,
) -> None:
    """Register a Search Provider with the given name and fetch_endpoint.

    Both have to be unique and if not raises AlreadyExistsError.
    The fetch_endpoint is used by clients to fetch the article from the Search Provider.

    :param name: Search Provider Name
    :param fetch_endpoint: relative url to /api
    :param provider_class: provider implementation
    :param label: label to use (None to use provider_class.label or name in this order)
    :raises: AlreadyExistsError - if a search has been registered with either name or fetch_endpoint.
    """
    if fetch_endpoint is not None and not isinstance(fetch_endpoint, str):
        raise ValueError(_("fetch_endpoint must be a string"))

    if name in registered_search_providers:
        raise AlreadyExistsError(f"A Search Provider with name: {name} already exists")

    if not ((fetch_endpoint and not provider_class) or (not fetch_endpoint and provider_class)):
        raise ValueError(_("You have to specify either fetch_endpoint or provider_class."))

    if fetch_endpoint:
        existing_endpoints = {
            provider.endpoint for provider in registered_search_providers.values() if provider.endpoint
        }
        if fetch_endpoint in existing_endpoints:
            raise AlreadyExistsError(
                _("A Search Provider for the fetch endpoint: {endpoint} exists with name: {name}").format(
                    endpoint=fetch_endpoint, name=name
                )
            )

    if label is None:
        if provider_class is not None and hasattr(provider_class, "label") and provider_class.label:
            label = provider_class.label
        else:
            label = name

    registered_search_providers[name] = SearchProviderData(
        name=name, endpoint=fetch_endpoint, provider_class=provider_class, label=label
    )

    allowed_search_providers.append(name)


@endpoint("/search_providers_allowed", methods=["GET"], auth=[required_privilege_rule("search_providers")])
async def get_search_providers() -> Response:
    providers = [
        {"search_provider": provider.name, "label": provider.label} for provider in registered_search_providers.values()
    ]
    return Response(providers, 200)
