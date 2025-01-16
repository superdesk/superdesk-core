# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, List, Optional, Any, cast
import importlib

from superdesk.core.types import WSGIApp

from .auth.user_auth import UserAuthProtocol
from .privileges import PrivilegesRegistry


def get_app_config(key: str, default: Optional[Any] = None) -> Optional[Any]:
    if _global_app is not None:
        return _global_app.wsgi.config.get(key, default)

    from quart import current_app

    try:
        return current_app.config.get(key, default)
    except RuntimeError:
        pass

    raise RuntimeError("Superdesk app is not running")


class SuperdeskAsyncApp:
    _running: bool
    _imported_modules: Dict[str, "Module"]
    _module_configs: dict[str, dict]

    #: A class instance that adheres to the WSGI protocol
    wsgi: WSGIApp

    #: MongoResources instance used to manage mongo config, clients and resources
    mongo: "MongoResources"

    #: ElasticResources instance used to manage elastic config, clients and resources
    elastic: "ElasticResources"

    resources: "Resources"

    auth: UserAuthProtocol

    privileges: PrivilegesRegistry

    def __init__(self, wsgi: WSGIApp):
        self._running = False
        self._imported_modules = {}
        self._module_configs = {}
        self.wsgi = wsgi
        self.mongo = MongoResources(self)
        self.elastic = ElasticResources(self)
        self.resources = Resources(self)
        self.auth = self.load_auth_module()
        self._store_app()
        self.privileges = PrivilegesRegistry()

    @property
    def running(self) -> bool:
        """Returns ``True`` if the app is running"""

        return self._running

    def get_module_list(self) -> List["Module"]:
        """Returns the list of loaded modules, in descending order based on their priority"""

        return sorted(self._imported_modules.values(), key=lambda x: x.priority, reverse=True)

    def load_auth_module(self) -> UserAuthProtocol:
        auth_module_config = cast(
            str, self.wsgi.config.get("ASYNC_AUTH_CLASS", "superdesk.core.auth.token_auth:TokenAuthorization")
        )
        try:
            module_path, module_attribute = auth_module_config.split(":")
        except ValueError as error:
            raise RuntimeError(f"Invalid config ASYNC_AUTH_MODULE={auth_module_config}: {error}")

        imported_module = importlib.import_module(module_path)
        auth_class = getattr(imported_module, module_attribute)

        if not issubclass(auth_class, UserAuthProtocol):
            raise RuntimeError(f"Invalid config ASYNC_AUTH_MODULE={auth_module_config}, invalid auth type {auth_class}")

        return auth_class()

    def _load_modules(self, paths: List[str | tuple[str, dict]]):
        for path in paths:
            config: dict = {}
            if isinstance(path, tuple):
                path, config = path

            imported_module = importlib.import_module(path)
            module_instance = getattr(imported_module, "module", None)

            if module_instance is None:
                raise RuntimeError(f"Module '{path}' is missing a 'module' instance")
            elif not isinstance(module_instance, Module):
                raise RuntimeError(f"Module '{path}' is not a subclass of SuperdeskAsyncApp.Module")

            try:
                if self._imported_modules[module_instance.name].frozen:
                    raise RuntimeError(f"Module '{module_instance.name}' is frozen and cannot be overridden")
            except KeyError:
                pass

            module_instance.path = path
            self._imported_modules[module_instance.name] = module_instance
            self._module_configs[module_instance.name] = config

        # init all configs first (in case ``module.init`` requires config from another module)
        for module in self.get_module_list():
            if module.config is not None:
                module.config.load_from_dict(
                    self.wsgi.config,
                    prefix=module.config_prefix,
                    freeze=module.freeze_config,
                    additional=self._module_configs[module.name],
                )

        # Now register all resources
        for module in self.get_module_list():
            for resource_config in module.resources or []:
                self.resources.register(resource_config)

        # Now register all http endpoints
        for module in self.get_module_list():
            from .resources.resource_rest_endpoints import ResourceRestEndpoints

            for resource_config in module.resources or []:
                # If REST endpoints are enabled for this resource
                # then add the endpoint group to this module's `endpoints` config
                rest_endpoint_config = resource_config.rest_endpoints
                if rest_endpoint_config is None:
                    continue

                endpoint_class = rest_endpoint_config.endpoints_class or ResourceRestEndpoints
                self.wsgi.register_endpoint(endpoint_class(resource_config, rest_endpoint_config))

            for endpoint in module.endpoints or []:
                self.wsgi.register_endpoint(endpoint)

        # init all modules
        for module in self.get_module_list():
            if module.init is not None:
                module.init(self)

            # then register all module privileges
            for privilege in module.privileges or []:
                self.privileges.add(privilege)

    def start(self):
        """Start the app

        This loads all the modules, based on the :ref:`settings.modules` config

        :raises RuntimeError: if the app is already running
        :raises RuntimeError: if any module failed to load
        """

        if self.running:
            raise RuntimeError("App is already running")

        self._store_app()
        self._load_modules(self.wsgi.config.get("MODULES", []))
        self._running = True

        # after app is running is longer possible to add more privileges
        self.privileges.lock()

    def stop(self):
        """Stops the app

        This tells :attr:`MongoResources to stop <superdesk.core.mongo.MongoResources.stop>`, clears imported modules
        and sets :attr:`running <superdesk.core.app.SuperdeskAsyncApp.running>` to False
        """

        self.mongo.stop()
        self._imported_modules.clear()
        self._remove_app()
        self._running = False

    def _store_app(self):
        from quart import current_app

        try:
            setattr(current_app, "async_app", self)
        except RuntimeError:
            # Flask context not available
            pass

        global _global_app
        _global_app = self

    def _remove_app(self):
        from quart import current_app

        try:
            setattr(current_app, "async_app", None)
        except RuntimeError:
            # Flask context not available
            pass

        global _global_app
        _global_app = None


def get_current_app() -> WSGIApp:
    """Retrieve the current WSGI app instance"""

    from quart import current_app

    return cast(WSGIApp, current_app)


def get_current_async_app() -> SuperdeskAsyncApp:
    """Retrieve the current app instance"""

    global _global_app

    if _global_app is not None:
        return _global_app

    from quart import current_app

    try:
        async_app = getattr(current_app, "async_app", None)
        if async_app is not None:
            return async_app
    except RuntimeError:
        # Flask context not available
        pass

    raise RuntimeError("Superdesk app is not running")


def get_current_auth() -> UserAuthProtocol:
    return get_current_async_app().auth


_global_app: Optional[SuperdeskAsyncApp] = None


from .module import Module  # noqa: E402
from .mongo import MongoResources  # noqa: E402
from .elastic import ElasticResources  # noqa: E402
from .resources import Resources  # noqa: E402
