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
from flask.ext.script import Command as BaseCommand, Option  # noqa
from werkzeug.exceptions import HTTPException
from eve.utils import config  # noqa
from eve.methods.common import document_link  # noqa

from .eve_backend import EveBackend
from .datalayer import SuperdeskDataLayer  # noqa
from .services import BaseService as Service  # noqa
from .resource import Resource  # noqa
from .privilege import privilege, intrinsic_privilege, get_intrinsic_privileges  # noqa
from .workflow import *  # noqa


API_NAME = 'Superdesk API'
VERSION = (0, 0, 1)
SCHEMA_VERSION = 0
DOMAIN = {}
COMMANDS = {}
BLUEPRINTS = []
JINJA_FILTERS = dict()
app_components = dict()
app_models = dict()
resources = dict()
eve_backend = EveBackend()
default_user_preferences = dict()
default_session_preferences = dict()
signals = blinker.Namespace()

logger = logging_lib.getLogger(__name__)


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


def blueprint(blueprint, **kwargs):
    """Register blueprint"""
    blueprint.kwargs = kwargs
    BLUEPRINTS.append(blueprint)


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


def register_resource(name, resource, service=None, backend=None, privilege=None):
    """Shortcut for registering resource and service together.

    :param name: resource name
    :param resource: resource class
    :param service: service class
    :param backend: backend instance
    :param privilege: privilege to register with resource
    """
    if not backend:
        backend = get_backend()
    if not service:
        service = Service
    if privilege:
        intrinsic_privilege(name, privilege)
    service_instance = service(name, backend=backend)
    resource(name, app=app, service=service_instance)


def register_jinja_filter(name, jinja_filter):
    """Register jinja filter

    :param str name: name of the filter
    :param jinja_filter: jinja filter function
    """
    JINJA_FILTERS[name] = jinja_filter
