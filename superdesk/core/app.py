# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, List, Optional
import importlib

from .wsgi import WSGIApp


class SuperdeskAsyncApp:
    _running: bool
    _imported_modules: Dict[str, "Module"]

    #: A class instance that adheres to the WSGI protocol
    wsgi: WSGIApp

    #: MongoResources instance used to manage mongo config, clients and resources
    mongo: "MongoResources"

    #: ElasticResources instance used to manage elastic config, clients and resources
    elastic: "ElasticResources"

    resources: "Resources"

    def __init__(self, wsgi: WSGIApp):
        self._running = False
        self._imported_modules = {}
        self.wsgi = wsgi
        self.mongo = MongoResources(self)
        self.elastic = ElasticResources(self)
        self.resources = Resources(self)

    @property
    def running(self) -> bool:
        """Returns ``True`` if the app is running"""

        return self._running

    def get_module_list(self) -> List["Module"]:
        """Returns the list of loaded modules, in descending order based on their priority"""

        return sorted(self._imported_modules.values(), key=lambda x: x.priority, reverse=True)

    def _load_modules(self, paths: List[str]):
        for path in paths:
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

        # init all configs first (in case ``module.init`` requires config from another module)
        for module in self.get_module_list():
            if module.config is not None:
                module.config.load_from_dict(
                    self.wsgi.config,
                    prefix=module.config_prefix,
                    freeze=module.freeze_config,
                )

        # Now register all resources
        for module in self.get_module_list():
            for resource_config in module.resources or []:
                self.resources.register(resource_config)

        # then init all modules
        for module in self.get_module_list():
            if module.init is not None:
                module.init(self)

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
        from flask import current_app

        try:
            setattr(current_app, "async_app", self)
        except RuntimeError:
            # Flask context not available
            pass

        global _global_app
        _global_app = self

    def _remove_app(self):
        from flask import current_app

        try:
            setattr(current_app, "async_app", None)
        except RuntimeError:
            # Flask context not available
            pass

        global _global_app
        _global_app = None


def get_current_async_app() -> SuperdeskAsyncApp:
    """Retrieve the current app instance"""

    from flask import current_app

    try:
        if current_app.async_app is not None:
            return current_app.async_app
    except RuntimeError:
        # Flask context not available
        pass

    global _global_app

    if _global_app is None:
        raise RuntimeError("Superdesk app is not running")

    return _global_app


_global_app: Optional[SuperdeskAsyncApp] = None


from .module import Module  # noqa: E402
from .mongo import MongoResources  # noqa: E402
from .elastic import ElasticResources  # noqa: E402
from .resources import Resources  # noqa: E402
