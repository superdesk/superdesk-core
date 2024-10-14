#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Type, Optional, Union, Mapping, cast, NoReturn

import os
import eve
from werkzeug.exceptions import NotFound
import jinja2
import importlib
import superdesk
import logging

from flask_mail import Mail
from eve.auth import TokenAuth
from eve.io.mongo.mongo import _create_index as create_index
from eve.io.media import MediaStorage
from eve.render import send_response
from quart_babel import Babel
from babel import parse_locale
from pymongo.errors import DuplicateKeyError

from superdesk.commands import configure_cli
from superdesk.flask import (
    g,
    url_for,
    Config,
    Request as FlaskRequest,
    Blueprint,
    request as flask_request,
    redirect,
    session,
)
from superdesk.celery_app import init_celery
from superdesk.datalayer import SuperdeskDataLayer  # noqa
from superdesk.errors import SuperdeskError, SuperdeskApiError, DocumentError
from superdesk.factory.sentry import SuperdeskSentry
from superdesk.logging import configure_logging
from superdesk.storage import ProxyMediaStorage
from superdesk.validator import SuperdeskValidator
from superdesk.json_utils import SuperdeskFlaskJSONProvider, SuperdeskJSONEncoder
from superdesk.cache import cache_backend

from .elastic_apm import setup_apm
from superdesk.core.types import (
    DefaultNoValue,
    Endpoint,
    Request,
    RequestStorage,
    RequestSessionStorageProvider,
    EndpointGroup,
    HTTP_METHOD,
    Response,
)
from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.resources import ResourceModel
from superdesk.core.web import NullEndpoint

SUPERDESK_PATH = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

logger = logging.getLogger(__name__)


class FlaskStorageProvider:
    @property
    def _store(self):
        raise NotImplementedError()

    def get(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        return self._store.get(key, default) if default is not DefaultNoValue else self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        setattr(self._store, key, value)
        # self._store[key] = value

    def pop(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        return self._store.pop(key, default) if default is not DefaultNoValue else self._store.pop(key)


class FlaskSessionStorage(RequestSessionStorageProvider):
    def get(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        return session.get(key, default) if default is not DefaultNoValue else session.get(key)

    def set(self, key: str, value: Any) -> None:
        session[key] = value

    def pop(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        session.pop(key, default) if default is not DefaultNoValue else session.pop(key)

    def set_session_permanent(self, value: bool) -> None:
        session.permanent = value

    def is_session_permanent(self) -> bool:
        return session.permanent

    def clear(self):
        session.clear()


class FlaskRequestStorage(FlaskStorageProvider):
    def get(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        return g.get(key, default) if default is not DefaultNoValue else g.get(key)

    def set(self, key: str, value: Any) -> None:
        setattr(g, key, value)

    def pop(self, key: str, default: Any | None = DefaultNoValue) -> Any:
        g.pop(key, default) if default is not DefaultNoValue else g.pop(key)


class HttpFlaskRequestStorage(RequestStorage):
    session = FlaskSessionStorage()
    request = FlaskRequestStorage()


class HttpFlaskRequest(Request):
    endpoint: Endpoint
    request: FlaskRequest
    storage = HttpFlaskRequestStorage()
    user: Any | None

    def __init__(self, endpoint: Endpoint, request: FlaskRequest):
        self.endpoint = endpoint
        self.request = request
        self.user = None

    @property
    def method(self) -> HTTP_METHOD:
        return cast(HTTP_METHOD, self.request.method)

    @property
    def url(self) -> str:
        return self.request.url

    @property
    def path(self) -> str:
        return self.request.path

    def get_header(self, key: str) -> Optional[str]:
        return self.request.headers.get(key)

    async def get_json(self) -> Union[Any, None]:
        return await self.request.get_json()

    async def get_form(self) -> Mapping:
        return (await self.request.form).deepcopy()

    async def get_data(self) -> Union[bytes, str]:
        return await self.request.get_data()

    async def abort(self, code: int, *args: Any, **kwargs: Any) -> NoReturn:
        from quart import abort

        abort(code, *args, **kwargs)

    def get_view_args(self, key: str) -> str | None:
        return None if not self.request.view_args else self.request.view_args.get(key, None)

    def get_url_arg(self, key: str) -> str | None:
        return self.request.args.get(key, None)

    def redirect(self, location: str, code: int = 302) -> Any:
        return redirect(location, code)


def set_error_handlers(app):
    """Set error handlers for the given application object.

    Each error handler receives a :py:class:`superdesk.errors.SuperdeskError`
    instance as a parameter and returns a tuple containing an error message
    that is sent to the client and the HTTP status code.

    :param app: an instance of `Eve <http://python-eve.org/>`_ application
    """

    @app.errorhandler(SuperdeskError)
    def client_error_handler(error):
        error_dict = error.to_dict()
        error_dict.update(internal_error=error.status_code)
        status_code = error.status_code or 422
        return send_response(None, (error_dict, None, None, status_code))

    @app.errorhandler(403)
    def server_forbidden_handler(error):
        return send_response(None, ({"code": 403, "error": error.response}, None, None, 403))

    @app.errorhandler(AssertionError)
    def assert_error_handler(error):
        return send_response(None, ({"code": 400, "error": str(error) if str(error) else "assert"}, None, None, 400))

    @app.errorhandler(DocumentError)
    def document_error_handler(error):
        return send_response(None, ({"code": 400, "error": str(error) if str(error) else "assert"}, None, None, 400))

    @app.errorhandler(500)
    def server_error_handler(error):
        """Log server errors."""
        return_error = SuperdeskApiError.internalError(error)
        return client_error_handler(return_error)


class SuperdeskEve(eve.Eve):
    async_app: SuperdeskAsyncApp
    _endpoints: list[Endpoint]
    _endpoint_groups: list[EndpointGroup]
    _endpoint_lookup: dict[str, Endpoint | EndpointGroup]

    media: Any
    data: Any

    def __init__(self, **kwargs):
        self.json_provider_class = SuperdeskFlaskJSONProvider
        self._endpoints = []
        self._endpoint_groups = []
        self._endpoint_lookup = {}
        super().__init__(**kwargs)
        self.async_app = SuperdeskAsyncApp(self)

        self.teardown_request(self._after_each_request)

    def __getattr__(self, name):
        """Only use events for on_* methods."""
        if name.startswith("on_"):
            return super(SuperdeskEve, self).__getattr__(name)
        raise AttributeError("type object '%s' has no attribute '%s'" % (self.__class__.__name__, name))

    def init_indexes(self, ignore_duplicate_keys=False):
        for resource, resource_config in self.config["DOMAIN"].items():
            mongo_indexes = resource_config.get("mongo_indexes__init")
            if not mongo_indexes:
                continue

            # Borrowed https://github.com/pyeve/eve/blob/22ea4bfebc8b633251cd06837893ff699bd07a00/eve/flaskapp.py#L915
            for name, value in mongo_indexes.items():
                if isinstance(value, tuple):
                    list_of_keys, index_options = value
                else:
                    list_of_keys = value
                    index_options = {}

                # index creation in background
                index_options.setdefault("background", True)

                try:
                    create_index(self, resource, name, list_of_keys, index_options)
                except KeyError:
                    logger.warning("resource config missing for %s", resource)
                    continue
                except DuplicateKeyError as err:
                    # Duplicate key for unique indexes are generally caused by invalid documents in the collection
                    # such as multiple documents not having a value for the attribute used for the index
                    # Log the error so it can be diagnosed and fixed
                    logger.exception(err)

                    if not ignore_duplicate_keys:
                        raise

        self.async_app.mongo.create_indexes_for_all_resources()

    def item_scope(self, name, schema=None):
        """Register item scope."""
        self.config.setdefault("item_scope", {})[name] = {
            "schema": schema,
        }

        def update_resource_schema(resource):
            assert schema
            self.config["DOMAIN"][resource]["schema"].update(schema)
            for key in schema:
                self.config["DOMAIN"][resource]["datasource"]["projection"][key] = 1

        if schema is not None:
            for resource in ("archive", "archive_autosave", "published", "archived"):
                update_resource_schema(resource)
                versioned_resource = resource + self.config["VERSIONS"]
                if versioned_resource in self.config["DOMAIN"]:
                    update_resource_schema(versioned_resource)

    def register_endpoint(self, endpoint: Endpoint | EndpointGroup):
        if isinstance(endpoint, EndpointGroup):
            blueprint = Blueprint(endpoint.name, endpoint.import_name)
            for sub_endpoint in endpoint.endpoints:
                blueprint.add_url_rule(
                    (
                        f"{self.api_prefix}/{sub_endpoint.url}"
                        if endpoint.url_prefix is None and not sub_endpoint.url.startswith("/")
                        else sub_endpoint.url
                    ),
                    sub_endpoint.name,
                    view_func=self._process_async_endpoint,
                    methods=sub_endpoint.methods,
                )
                self._endpoints.append(sub_endpoint)
            self.register_blueprint(blueprint)
            self._endpoint_groups.append(endpoint)
        else:
            url = f"{self.api_prefix}/{endpoint.url}" if not endpoint.url.startswith("/") else endpoint.url

            self.add_url_rule(
                url,
                endpoint.name,
                view_func=self._process_async_endpoint,
                methods=endpoint.methods,
            )
            self._endpoints.append(endpoint)

    def get_endpoint_for_current_request(self) -> Endpoint | None:
        if not flask_request or flask_request.endpoint is None:
            return None

        lookup_name = endpoint_name = flask_request.endpoint

        try:
            return self._endpoint_lookup[lookup_name]
        except KeyError:
            pass

        # Using the requests Blueprint, determine if this request is for an EndpointGroup
        blueprint_name = flask_request.blueprint
        endpoint_group = (
            None
            if not blueprint_name
            else next((group for group in self._endpoint_groups if group.name == blueprint_name), None)
        )
        endpoint: Optional[Endpoint] = None
        if endpoint_group is not None:
            # It seems this request is for an EndpointGroup
            # Try and find the specific Endpoint this request is for
            endpoint_name = endpoint_name.replace(f"{blueprint_name}.", "")
            endpoint = next((e for e in endpoint_group.endpoints if e.name == endpoint_name), None)

        # We were unable to find the Endpoint, falling back to directly registered endpoints
        if endpoint is None:
            endpoint = next((e for e in self._endpoints if e.name == endpoint_name), None)

        if endpoint is not None:
            self._endpoint_lookup[lookup_name] = endpoint

        return endpoint

    def _after_each_request(self, *args, **kwargs):
        g._request_instance = None
        g.user_instance = None
        g.company_instance = None

    async def _process_async_endpoint(self, **kwargs):
        request = self.get_current_request()

        # We were still unable to find the final Endpoint, return a 404 now
        if request is None:
            raise NotFound()

        response = await request.endpoint(
            kwargs,
            dict(flask_request.args.deepcopy()),
            request,
        )

        return (
            response if not isinstance(response, Response) else (response.body, response.status_code, response.headers)
        )

    def get_current_user_dict(self) -> dict[str, Any] | None:
        return getattr(g, "user", None)

    def download_url(self, media_id: str) -> str:
        prefered_url_scheme = self.config.get("PREFERRED_URL_SCHEME", "http")
        return url_for("download_raw.download_file", id=media_id, _external=True, _scheme=prefered_url_scheme)

    def as_any(self) -> Any:
        return self

    def get_current_request(self, req=None) -> HttpFlaskRequest | None:
        try:
            if not flask_request and not req:
                return None
        except AttributeError:
            return None

        existing_instance = g.get("_request_instance", None)
        if existing_instance:
            return cast(HttpFlaskRequest, existing_instance)

        endpoint = self.get_endpoint_for_current_request() or NullEndpoint
        new_request = HttpFlaskRequest(endpoint, req or flask_request)
        g._request_instance = new_request  # type: ignore[attr-defined]
        if not new_request.user:
            new_request.user = self.async_app.auth.get_current_user(new_request)
        return new_request


def get_media_storage_class(app_config: Dict[str, Any], use_provider_config: bool = True) -> Type[MediaStorage]:
    if use_provider_config and app_config.get("MEDIA_STORAGE_PROVIDER"):
        if isinstance(app_config["MEDIA_STORAGE_PROVIDER"], str):
            module_name, class_name = app_config["MEDIA_STORAGE_PROVIDER"].rsplit(".", 1)
            module = importlib.import_module(module_name)
            klass = getattr(module, class_name)
            if not issubclass(klass, MediaStorage):
                raise SystemExit("Invalid setting MEDIA_STORAGE_PROVIDER. Class must extend eve.io.media.MediaStorage")
            return klass

    return ProxyMediaStorage


def get_app(config=None, media_storage=None, config_object=None, init_elastic=None):
    """App factory.

    :param config: configuration that can override config from ``default_settings.py``
    :param media_storage: media storage class to use
    :param config_object: config object to load (can be module name, module or an object)
    :param init_elastic: obsolete config - kept there for BC
    :return: a new SuperdeskEve app instance
    """

    abs_path = SUPERDESK_PATH
    app_config = Config(abs_path)
    app_config.from_object("superdesk.default_settings")
    app_config.setdefault("APP_ABSPATH", abs_path)
    app_config.setdefault("DOMAIN", {})
    app_config.setdefault("SOURCES", {})

    if config_object:
        app_config.from_object(config_object)

    try:
        app_config.update(config or {})
    except TypeError:
        app_config.from_object(config)

    if not media_storage:
        media_storage = get_media_storage_class(app_config)

    app = SuperdeskEve(
        data=SuperdeskDataLayer,
        auth=TokenAuth,
        media=media_storage,
        settings=app_config,
        json_encoder=SuperdeskJSONEncoder,
        validator=SuperdeskValidator,
        template_folder=os.path.join(abs_path, "templates"),
    )

    app.jinja_options = {"autoescape": False}

    # init client_config with default config
    app.client_config = {
        "content_expiry_minutes": app.config.get("CONTENT_EXPIRY_MINUTES", 0),
        "ingest_expiry_minutes": app.config.get("INGEST_EXPIRY_MINUTES", 0),
    }

    superdesk.app = app
    app.async_app.start()

    custom_loader = jinja2.ChoiceLoader(
        [
            jinja2.FileSystemLoader("templates"),
            jinja2.FileSystemLoader(os.path.join(SUPERDESK_PATH, "templates")),
        ]
    )

    app.jinja_loader = custom_loader
    app.mail = Mail(app)
    app.sentry = SuperdeskSentry(app)
    cache_backend.init_app(app)
    setup_apm(app)

    # setup babel
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", os.path.join(SUPERDESK_PATH, "translations"))
    babel = Babel(app, configure_jinja=False)

    # TODO: Fix this after Flask3 upgrade
    # @babel.localeselector
    # def get_locale():
    #     user = getattr(g, "user", {})
    #     user_language = user.get("language", app.config.get("DEFAULT_LANGUAGE", "en"))
    #     try:
    #         # Attempt to load the local using Babel.parse_local
    #         parse_locale(user_language.replace("-", "_"))
    #     except ValueError:
    #         # If Babel fails to recognise the locale, then use the default language
    #         user_language = app.config.get("DEFAULT_LANGUAGE", "en")
    #
    #     return user_language.replace("-", "_")

    set_error_handlers(app)

    @app.after_request
    def after_request(response):
        # fixing previous media prefixes if defined
        if app.config["MEDIA_PREFIXES_TO_FIX"] and app.config["MEDIA_PREFIX"]:
            current_prefix = app.config["MEDIA_PREFIX"].rstrip("/").encode()
            for prefix in app.config["MEDIA_PREFIXES_TO_FIX"]:
                response.data = response.data.replace(prefix.rstrip("/").encode(), current_prefix)
        return response

    init_celery(app)

    installed = set()

    def install_app(module_name):
        if module_name in installed:
            return
        installed.add(module_name)
        app_module = importlib.import_module(module_name)
        if hasattr(app_module, "init_app"):
            app_module.init_app(app)

    for module_name in app.config.get("CORE_APPS", []):
        install_app(module_name)

    for module_name in app.config.get("INSTALLED_APPS", []):
        install_app(module_name)

    app.config.setdefault("DOMAIN", {})
    for resource in superdesk.DOMAIN:
        if resource not in app.config["DOMAIN"]:
            app.register_resource(resource, superdesk.DOMAIN[resource])

    for name, jinja_filter in superdesk.JINJA_FILTERS.items():
        app.jinja_env.filters[name] = jinja_filter

    configure_logging(app.config["LOG_CONFIG_FILE"])

    # configure the CLI only after modules and apps have been loaded
    # to make sure all commands are registered
    configure_cli(app)

    return app


SuperdeskApp = SuperdeskEve
