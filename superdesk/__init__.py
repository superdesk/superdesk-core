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

import blinker
import logging as logging_lib
from flask import abort, json, Blueprint, current_app as app  # noqa
from flask_script import Command as BaseCommand, Option  # noqa
from werkzeug.exceptions import HTTPException
from eve.utils import config  # noqa
from eve.methods.common import document_link  # noqa

from .eve_backend import EveBackend
from .datalayer import SuperdeskDataLayer  # noqa
from .services import BaseService as Service  # noqa
from .resource import Resource  # noqa
from .privilege import privilege, intrinsic_privilege, get_intrinsic_privileges  # noqa
from .workflow import *  # noqa

__version__ = '1.9rc1'

API_NAME = 'Superdesk API'
SCHEMA_VERSION = 0
DOMAIN = {}
COMMANDS = {}
JINJA_FILTERS = dict()
app_components = dict()
app_models = dict()
resources = dict()
eve_backend = EveBackend()
default_user_preferences = dict()
default_session_preferences = dict()
signals = blinker.Namespace()
logger = logging_lib.getLogger(__name__)

# core signals
item_published = signals.signal('item:published')
item_update = signals.signal('item:update')


class Command(BaseCommand):
    """Superdesk Command.

    The Eve framework changes introduced with https://github.com/nicolaiarocci/eve/issues/213 make the commands fail.
    Reason being the flask-script's run the commands using test_request_context() which is invalid.
    That's the reason we are inheriting the Flask-Script's Command to overcome this issue.
    """

    def __call__(self, _app=None, *args, **kwargs):
        try:
            with app.app_context():
                res = self.run(*args, **kwargs)
                logger.info('Command finished with: {}'.format(res))
                return 0
        except Exception as ex:
            logger.info('Uhoh, an exception occured while running the command...')
            logger.exception(ex)
            return 1


def get_headers(self, environ=None):
    """Fix CORS for abort responses.

    todo(petr): put in in custom flask error handler instead
    """
    return [
        ('Content-Type', 'text/html'),
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Headers', '*'),
    ]


setattr(HTTPException, 'get_headers', get_headers)


def domain(resource, res_config):
    """Register domain resource"""
    DOMAIN[resource] = res_config


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
    return eve_backend


def get_resource_service(resource_name):
    return resources[resource_name].service


def get_resource_privileges(resource_name):
    attr = getattr(resources[resource_name], 'privileges', {})
    return attr


def register_default_user_preference(preference_name, preference):
    default_user_preferences[preference_name] = preference


def register_default_session_preference(preference_name, preference):
    default_session_preferences[preference_name] = preference


def register_resource(name, resource, service=None, backend=None, privilege=None, _app=None):
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
    service_instance = service(name, backend=backend)
    resource(name, app=_app, service=service_instance)


def register_jinja_filter(name, jinja_filter):
    """Register jinja filter

    :param str name: name of the filter
    :param jinja_filter: jinja filter function
    """
    JINJA_FILTERS[name] = jinja_filter


from superdesk.search_provider import SearchProvider  # noqa
from apps.search_providers import register_search_provider  # noqa
