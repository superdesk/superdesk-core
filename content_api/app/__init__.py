# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
"""
A module that provides the Superdesk public API application object and runs
the Superdesk public API.

The API is built using the `Eve framework <http://python-eve.org/>`_ and is
thus essentially just a normal `Flask <http://flask.pocoo.org/>`_ application.

.. note:: The public API should not be confused with the "internal" API that
    is meant to be used by the Superdesk browser client only.
"""

import importlib
import logging
import os

from eve import Eve
from eve.io.mongo.mongo import MongoJSONEncoder
from eve.render import send_response
from raven.contrib.flask import Sentry
import raven.exceptions
from redis.client import StrictRedis

from content_api.app import settings
from content_api.auth.oauth2 import BearerAuth
from flask.ext.mail import Mail  # @UnresolvedImport
import superdesk
from superdesk.datalayer import SuperdeskDataLayer
from superdesk.errors import SuperdeskError, SuperdeskApiError
from superdesk.storage.desk_media_storage import SuperdeskGridFSMediaStorage
from superdesk.validator import SuperdeskValidator


logger = logging.getLogger('superdesk')

sentry = Sentry(register_signal=False, wrap_wsgi=False)


def _set_error_handlers(app):
    """Set error handlers for the given application object.

    Each error handler receives a :py:class:`superdesk.errors.SuperdeskError`
    instance as a parameter and returns a tuple containing an error message
    that is sent to the client and the HTTP status code.

    :param app: an instance of `Eve <http://python-eve.org/>`_ application
    """

    # TODO: contains the same bug as the client_error_handler of the main
    # superdesk app, fix it when the latter gets resolved (or, perhaps,
    # replace it with a new 500 error handler tailored for the public API app)
    @app.errorhandler(SuperdeskError)
    def client_error_handler(error):
        error_dict = error.to_dict()
        error_dict.update(internal_error=error.status_code)
        return send_response(None, (error_dict, None, None, 422))

    @app.errorhandler(500)
    def server_error_handler(error):
        """Log server errors."""
        if getattr(app, 'sentry'):
            app.sentry.captureException()
        logger.exception(error)
        return_error = SuperdeskApiError.internalError()
        return client_error_handler(return_error)


def get_app(config=None):
    """
    App factory.

    :param dict config: configuration that can override config
        from `settings.py`
    :return: a new SuperdeskEve app instance
    """
    if config is None:
        config = {}

    config.setdefault('SOURCES', {})
    config['APP_ABSPATH'] = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

    for key in dir(settings):
        if key.isupper():
            config.setdefault(key, getattr(settings, key))

    media_storage = SuperdeskGridFSMediaStorage
    if config.get('AMAZON_CONTAINER_NAME'):
        from superdesk.storage.amazon.amazon_media_storage import AmazonMediaStorage
        media_storage = AmazonMediaStorage

    app = Eve(
        auth=BearerAuth,
        settings=config,
        data=SuperdeskDataLayer,
        media=media_storage,
        json_encoder=MongoJSONEncoder,
        validator=SuperdeskValidator
    )

    superdesk.app = app
    _set_error_handlers(app)
    app.mail = Mail(app)
    if config.get('REDIS_URL'):
        app.redis = StrictRedis.from_url(config['REDIS_URL'], 0)

    for module_name in app.config['INSTALLED_APPS']:
        app_module = importlib.import_module(module_name)
        try:
            app_module.init_app(app)
        except AttributeError:
            pass

    for resource in config['DOMAIN']:
        app.register_resource(resource, config['DOMAIN'][resource])

    for blueprint in superdesk.BLUEPRINTS:
        prefix = app.api_prefix or None
        app.register_blueprint(blueprint, url_prefix=prefix)

    try:
        sentry.init_app(app)
    except (
        raven.exceptions.APIError,
        raven.exceptions.ConfigurationError,
        raven.exceptions.InvalidGitRepository
    ) as e:
        logger.error("Unable to init Sentry: {}".format(e))
    else:
        app.sentry = sentry

    return app
