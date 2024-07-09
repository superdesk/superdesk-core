# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk"""

import eve
import blinker
import click
import logging as logging_lib

from typing import Any, Dict, List, NamedTuple, Optional
from flask import Flask, abort, json, Blueprint, current_app
from flask.cli import ScriptInfo, with_appcontext
from flask_babel.speaklater import LazyString

# from flask_script import Command as BaseCommand, Option
from eve.utils import config  # noqa
from eve.methods.common import document_link  # noqa
from werkzeug.exceptions import HTTPException

from .eve_backend import EveBackend
from .datalayer import SuperdeskDataLayer  # noqa
from .services import BaseService as Service  # noqa
from .resource import Resource  # noqa
from .privilege import privilege, intrinsic_privilege, get_intrinsic_privileges  # noqa
from .workflow import *  # noqa
from .signals import *  # noqa
from apps.common.models.base_model import BaseModel
from apps.common.components.base_component import BaseComponent

__version__ = "3.0.0.dev0"

API_NAME = "Superdesk API"
SCHEMA_VERSION = 2
DOMAIN = {}
COMMANDS = {}
COMMANDS_V2 = []
JINJA_FILTERS = dict()
app_components: Dict[str, BaseComponent] = dict()
app_models: Dict[str, BaseModel] = dict()
resources: Dict[str, Resource] = dict()
_eve_backend = EveBackend()
default_user_preferences: Dict[str, "UserPreference"] = dict()
default_session_preferences: Dict[str, Any] = dict()
logger = logging_lib.getLogger(__name__)
app: Optional[eve.Eve] = None


class UserPreference(NamedTuple):
    value: Any
    label: Optional[LazyString] = None
    category: Optional[LazyString] = None


class Option(click.Option):
    """
    Basic Option class warpper of Click.Option that maintains compatibility with flask-script.
    """

    def __init__(self, *param_decls, action=None, dest=None, choices=None, **attrs):
        if action == "append":
            attrs["multiple"] = True

        elif action == "store_true":
            attrs["is_flag"] = True

        if dest:
            param_decls = list(param_decls) + [f"--{dest.replace('_', '-')}"]

        if choices:
            attrs["type"] = click.Choice(choices)

        super().__init__(param_decls, **attrs)


class Command(click.Command):
    """
    Basic Command wrapper class of Click.Command to maintain compatibility with previous flask-script
    implementations

    Attributes:
        name (str): The name of the command.
        option_list (list): A list of option instances.
    """

    name = None
    option_list: List[Option] = []

    def __init__(self, *args, **kwargs):
        # To avoid introducing too many breaking changes we need to set some
        # default values with the previous implementation with flask-script
        kwargs["params"] = kwargs.get("params", self.option_list)
        kwargs["callback"] = kwargs.get("run", self.run)

        # also to continue using the docstrings as help text
        kwargs["help"] = kwargs.get("help", self.__doc__)

        super().__init__(self.name, *args, **kwargs)

    def invoke(self, ctx):
        click.secho("DeprecationWarning: 'superdesk.Command' is deprecated. Use 'Click' library instead.", fg="yellow")
        return super().invoke(ctx)

    def run(self, *args, **kwargs):
        """
        Placeholder for the command's execution logic.

        Must be overridden by subclasses.

        Raises:
            NotImplementedError: If not overridden by subclasses.
        """
        raise NotImplementedError("Commands must implement the run method")


def register_command(command):
    COMMANDS_V2.append(command)


def get_headers(self, environ=None):
    """Fix CORS for abort responses.

    todo(petr): put in in custom flask error handler instead
    """
    return [
        ("Content-Type", "text/html"),
        ("Access-Control-Allow-Origin", current_app.config["CLIENT_URL"]),
        ("Access-Control-Allow-Headers", ",".join(current_app.config["X_HEADERS"])),
        ("Access-Control-Allow-Credentials", "true"),
        ("Access-Control-Allow-Methods", "*"),
    ]


setattr(HTTPException, "get_headers", get_headers)


def domain(resource, res_config):
    """Register domain resource"""
    app.register_resource(resource, res_config)


def command(name, command):
    """Register command"""
    COMMANDS[name] = command


def blueprint(blueprint, app, **kwargs):
    """Register flask blueprint.

    :param blueprint: blueprint instance
    :param app: flask app instance
    """
    blueprint.kwargs = kwargs
    prefix = app.api_prefix or None
    app.register_blueprint(blueprint, url_prefix=prefix, **kwargs)


def get_backend():
    """Returns the available backend, this will be changed in a factory if needed."""
    return _eve_backend


def get_resource_service(resource_name):
    return resources[resource_name].service


def get_resource_privileges(resource_name):
    attr = getattr(resources[resource_name], "privileges", {})
    return attr


def get_no_resource_privileges(resource_name):
    attr = getattr(resources[resource_name], "no_privileges", False)
    return attr


def register_default_user_preference(
    preference_name: str,
    preference: Dict[str, Any],
    label: Optional[LazyString] = None,
    category: Optional[LazyString] = None,
):
    # this part is temporary so I can update core before updating planning
    if label is None:
        label = preference.pop("label", None)
    if category is None:
        category = preference.pop("category", None)
    default_user_preferences[preference_name] = UserPreference(preference, label, category)


def register_default_session_preference(preference_name, preference):
    default_session_preferences[preference_name] = preference


def register_resource(name, resource, service=None, backend=None, privilege=None, _app=None, service_instance=None):
    """Shortcut for registering resource and service together.

    :param name: resource name
    :param resource: resource class
    :param service: service class
    :param backend: backend instance
    :param privilege: privilege to register with resource
    :param _app: flask app
    """
    if not backend:
        backend = get_backend()
    if not service:
        service = Service
    if privilege:
        intrinsic_privilege(name, privilege)
    if not _app:
        _app = app
    if service_instance is None:
        service_instance = service(name, backend=backend)
    else:
        service_instance.init(name, backend)
    resource(name, app=_app, service=service_instance)


def register_jinja_filter(name, jinja_filter):
    """Register jinja filter

    :param str name: name of the filter
    :param jinja_filter: jinja filter function
    """
    JINJA_FILTERS[name] = jinja_filter


def register_item_schema_field(name, schema, app, copy_on_rewrite=True):
    """Register new item schema field.

    .. versionadded:: 1.28

    :param str name: field name
    :param dict schema: field schema
    :param Flask app: flask app
    :param bool copy_on_rewrite: copy field value when rewriting item
    """
    for resource in ["ingest", "archive", "published", "archive_autosave"]:
        app.config["DOMAIN"][resource]["schema"].update({name: schema})
        app.config["DOMAIN"][resource]["datasource"]["projection"].update({name: 1})

    app.config["DOMAIN"]["content_templates_apply"]["schema"]["item"]["schema"].update({name: schema})

    if copy_on_rewrite:
        app.config.setdefault("COPY_ON_REWRITE_FIELDS", [])
        app.config["COPY_ON_REWRITE_FIELDS"].append(name)


from superdesk.search_provider import SearchProvider  # noqa
from apps.search_providers import register_search_provider  # noqa
