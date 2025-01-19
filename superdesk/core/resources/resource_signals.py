from typing import Generic, Any

from superdesk.core.types import Request, Response, SearchRequest
from superdesk.core.signals import AsyncSignal, SignalGroup

from .types import ResourceModelType

__all__ = [
    "global_signals",
    "ResourceDataSignals",
    "ResourceWebSignals",
    "ResourceSignals",
    "get_resource_signals",
    "clear_all_resource_signal_listeners",
]


#: Global signals, used for listening to all resource data/web signals
global_signals: "ResourceSignals"


class ResourceDataSignals(SignalGroup, Generic[ResourceModelType]):
    """
    A group of signals to be used on a resource data layer
    """

    signal_name_prefix = "resource:data:"

    #: Signal fired before a resource item is saved to the DB
    #:
    #: Params:
    #:     - item :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The item to be created
    on_create: AsyncSignal[ResourceModelType]

    #: Signal fired after a resource item has been saved to the DB
    #:
    #: * item :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The item that was created
    on_created: AsyncSignal[ResourceModelType]

    #: Signal fired before a resource item is updated in the DB
    #:
    #: Params:
    #:     - original :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The original item that is to be updated
    #:     - updates :class:`dict`: A dictionary of key/value pairs to update
    on_update: AsyncSignal[ResourceModelType, dict[str, Any]]

    #: Signal fired after a resource item has been updated in the DB
    #:
    #: Params:
    #:     - original :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The original item that was updated (without changes applied)
    #:     - updates :class:`dict`: A dictionary of key/value that was updated
    on_updated: AsyncSignal[ResourceModelType, dict[str, Any]]

    #: Signal fired before a resource item is to be deleted from the DB
    #:
    #: Params:
    #:     - item :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The item is to be deleted
    on_delete: AsyncSignal[ResourceModelType]

    #: Signal fired after a resource item has been deleted from the DB
    #:
    #: Params:
    #:     - item :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The item that was deleted
    on_deleted: AsyncSignal[ResourceModelType]


class ResourceWebSignals(SignalGroup, Generic[ResourceModelType]):
    """
    A group of signals to be used on a resource web api layer
    """

    signal_name_prefix = "resource:web:"

    #: Signal fired before processing a Web request to create a new resource item
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The Web request instance
    #:     - items :class:`list[ResourceModel] <superdesk.core.resources.model.ResourceModel>`: A list of items to be created
    on_create: AsyncSignal[Request, list[ResourceModelType]]

    #: Signal fired before sending Web response from a new resource request
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - response :class:`Response <superdesk.core.types.Response>`: The response to be returned to the client
    on_create_response: AsyncSignal[Request, Response]

    #: Signal fired before processing a Web request to update an existing resource item
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - original :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The original item that is to be updated
    #:     - updates :class:`dict`: A dictionary of key/value pairs to update
    on_update: AsyncSignal[Request, ResourceModelType, dict[str, Any]]

    #: Signal fired before sending Web response from an update resource request
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - response :class:`Response <superdesk.core.types.Response>`: The response to be returned to the client
    on_update_response: AsyncSignal[Request, Response]

    #: Signal fired before processing a Web request to delete a resource item
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - item :class:`ResourceModel <superdesk.core.resources.model.ResourceModel>`: The resource item to be deleted
    on_delete: AsyncSignal[Request, ResourceModelType]

    #: Signal fired before sending Web response from a delete resource request
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - response :class:`Response <superdesk.core.types.Response>`: The response to be returned to the client
    on_delete_response: AsyncSignal[Request, Response]

    #: Signal fired before processing a Web request to get a resource item
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    on_get: AsyncSignal[Request]

    #: Signal fired before sending Web response from a get resource item request
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - response :class:`Response <superdesk.core.types.Response>`: The response to be returned to the client
    on_get_response: AsyncSignal[Request, Response]

    #: Signal fired before processing a Web request to search for resource items
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The Web request instance
    #:     - search :class:`SearchRequest <superdesk.core.types.SearchRequest>`: The search request instance
    on_search: AsyncSignal[Request, SearchRequest]

    #: Signal fired before sending Web response from a search resource items request
    #:
    #: Params:
    #:     - request :class:`Request <superdesk.core.types.Request>`: The web request instance
    #:     - response :class:`Response <superdesk.core.types.Response>`: The response to be returned to the client
    on_search_response: AsyncSignal[Request, Response]


class ResourceSignals(SignalGroup, Generic[ResourceModelType]):
    """
    A group of resource signals, combining both data and web api signals
    """

    #: Data signals sent when interacting with the DB
    data: ResourceDataSignals[ResourceModelType]

    #: Web signals sent when receiving REST request through API
    web: ResourceWebSignals[ResourceModelType]

    #: Flag to indicate if this resource should connect to global resource signal, defaults to ``True``
    connect_to_global: bool

    def __init__(self, connect_to_global: bool = True):
        super().__init__()
        self.connect_to_global = connect_to_global
        self.data = ResourceDataSignals()
        self.web = ResourceWebSignals()

        if self.connect_to_global:
            global global_signals
            self.data.connect_group(global_signals.data)
            self.web.connect_group(global_signals.web)

    def clear_listeners(self) -> None:
        super().clear_listeners()
        if self.connect_to_global:
            global global_signals
            self.data.connect_group(global_signals.data)
            self.web.connect_group(global_signals.web)


global_signals = ResourceSignals(False)
_resource_signal_store: dict[str, ResourceSignals] = {}


def get_resource_signals(resource_model_class: type[ResourceModelType]) -> ResourceSignals[ResourceModelType]:
    """Get the ``ResourceSignals`` instance for the provided resource type"""

    try:
        return _resource_signal_store[resource_model_class.model_resource_name]
    except KeyError:
        _resource_signal_store[resource_model_class.model_resource_name] = ResourceSignals[ResourceModelType]()
        return _resource_signal_store[resource_model_class.model_resource_name]


def clear_all_resource_signal_listeners() -> None:
    """Clear all listeners from all registered resource signals"""

    for resource_signals in _resource_signal_store.values():
        resource_signals.clear_listeners()
    global_signals.clear_listeners()
