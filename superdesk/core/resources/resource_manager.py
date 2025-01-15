from copy import deepcopy

from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.signals import SignalGroup, Signal

from .service import AsyncResourceService
from .resource_config import ResourceConfig


class Resources(SignalGroup):
    """A high level resource class used to manage all resources in the system"""

    _resource_configs: dict[str, ResourceConfig]

    _resource_services: dict[str, AsyncResourceService]

    signal_name_prefix = "resources:"

    #: Signal fired when a new resource was just registered with the system
    on_resource_registered: Signal[SuperdeskAsyncApp, ResourceConfig]

    #: A reference back to the parent app, for configuration purposes
    app: SuperdeskAsyncApp

    def __init__(self, app: SuperdeskAsyncApp):
        # TODO-ASYNC: Do we need to manually initialise this signal???
        self.on_resource_registered = Signal("resources:on_resource_registered")

        super().__init__()
        self._resource_configs = {}
        self._resource_services = {}
        self.app = app

    def register(self, config: ResourceConfig):
        """Register a new resource in the system

        This will also register the resource with Mongo and optionally Elasticsearch

        :param config: A ResourceConfig of the resource to be registered
        :raises KeyError: If the resource has already been registered
        """

        if config.name in self._resource_configs:
            raise KeyError(f"Resource '{config.name}' already registered")

        self._resource_configs[config.name] = config

        config.data_class.model_resource_name = config.name
        if not config.datasource_name:
            config.datasource_name = config.name

        self.register_service(config)
        self.on_resource_registered.send(self.app, config)

    def register_service(self, config: ResourceConfig):
        if config.service is None:

            class GenericResourceService(AsyncResourceService):
                pass

            GenericResourceService.resource_name = config.name
            GenericResourceService.config = config
            config.service = GenericResourceService

        config.service.resource_name = config.name
        self._resource_services[config.name] = config.service()

    def get_config(self, name: str) -> ResourceConfig:
        """Get the config for a registered resource

        :param name: The name of the registered resource
        :return: A copy of the ResourceConfig of the registered resource
        :raises KeyError: If the resource is not registered
        """

        return deepcopy(self._resource_configs[name])

    def get_all_configs(self) -> list[ResourceConfig]:
        """Get a copy of the configs for all the registered resources in the system"""

        return deepcopy(list(self._resource_configs.values()))

    def get_resource_service(self, resource_name: str) -> AsyncResourceService:
        return self._resource_services[resource_name]
