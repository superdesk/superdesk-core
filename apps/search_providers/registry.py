
from superdesk import Resource, Service
from superdesk.utils import ListCursor
from superdesk.errors import AlreadyExistsError


registered_search_providers = {}
allowed_search_providers = []


def register_search_provider(name, fetch_endpoint=None, provider_class=None, label=None):
    """Register a Search Provider with the given name and fetch_endpoint.

    Both have to be unique and if not raises AlreadyExistsError.
    The fetch_endpoint is used by clients to fetch the article from the Search Provider.

    :param name: Search Provider Name
    :type name: str
    :param fetch_endpoint: relative url to /api
    :type fetch_endpoint: str
    :param provider_class: provider implementation
    :type provider: superdesk.SearchProvider
    :param label: label to use (None to use provider_class.label or name in this order)
    :type label: str
    :raises: AlreadyExistsError - if a search has been registered with either name or fetch_endpoint.
    """
    if fetch_endpoint is not None and not isinstance(fetch_endpoint, str):
        raise ValueError("fetch_enpoint must be a string")
    if name in registered_search_providers:
        raise AlreadyExistsError("A Search Provider with name: {} already exists".format(name))

    if not ((fetch_endpoint and not provider_class) or (not fetch_endpoint and provider_class)):
        raise ValueError('You have to specify either fetch_endpoint or provider_class.')

    provider_data = {}

    if fetch_endpoint:
        existing_endpoints = {d['endpoint'] for d in registered_search_providers.values() if 'endpoint' in d}
        if fetch_endpoint in existing_endpoints:
            raise AlreadyExistsError("A Search Provider for the fetch endpoint: {} exists with name: {}"
                                     .format(fetch_endpoint, registered_search_providers[name]))
        provider_data['endpoint'] = fetch_endpoint
    else:
        provider_data['class'] = provider_class

    if label is not None:
        provider_data['label'] = label
    elif provider_class is not None and hasattr(provider_class, 'label') and provider_class.label:
        provider_data['label'] = provider_class.label
    else:
        provider_data['label'] = name

    provider_data = registered_search_providers[name] = provider_data

    allowed_search_providers.append(name)


class SearchProviderAllowedResource(Resource):
    resource_methods = ['GET']
    item_methods = []


class SearchProviderAllowedService(Service):

    def get(self, req, lookup):
        def provider(provider_id):
            provider_data = registered_search_providers[provider_id]
            return {
                'search_provider': provider_id,
                'label': provider_data['label']
            }

        return ListCursor(
            [provider(_id) for _id in registered_search_providers]
        )
