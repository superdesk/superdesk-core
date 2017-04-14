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

import flask
import importlib

from eve import Eve
from eve.render import send_response
from eve.io.mongo.mongo import MongoJSONEncoder

from content_api.tokens import SubscriberTokenAuth
from superdesk.datalayer import SuperdeskDataLayer
from superdesk.errors import SuperdeskError, SuperdeskApiError
from superdesk.storage import SuperdeskGridFSMediaStorage
from superdesk.validator import SuperdeskValidator
from superdesk.factory.sentry import SuperdeskSentry


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
        status_code = error.status_code or 422
        return send_response(None, (error_dict, None, None, status_code))

    @app.errorhandler(500)
    def server_error_handler(error):
        """Log server errors."""
        return_error = SuperdeskApiError.internalError(error)
        return client_error_handler(return_error)


def get_app(config=None):
    """
    App factory.

    :param dict config: configuration that can override config
        from `settings.py`
    :return: a new SuperdeskEve app instance
    """
    app_config = flask.Config('.')

    # get content api default conf
    app_config.from_object('content_api.app.settings')

    # set some required fields
    app_config.update({'DOMAIN': {'upload': {}}, 'SOURCES': {}})

    try:
        # override from settings module, but only things defined in default config
        import settings as server_settings
        for key in dir(server_settings):
            if key.isupper() and key in app_config:
                app_config[key] = getattr(server_settings, key)
    except ImportError:
        pass  # if exists

    if config:
        app_config.update(config)

    media_storage = SuperdeskGridFSMediaStorage
    if app_config.get('AMAZON_CONTAINER_NAME'):
        from superdesk.storage import AmazonMediaStorage
        media_storage = AmazonMediaStorage

    app = Eve(
        auth=SubscriberTokenAuth,
        settings=app_config,
        data=SuperdeskDataLayer,
        media=media_storage,
        json_encoder=MongoJSONEncoder,
        validator=SuperdeskValidator
    )

    _set_error_handlers(app)

    for module_name in app.config.get('CONTENTAPI_INSTALLED_APPS', []):
        app_module = importlib.import_module(module_name)
        try:
            app_module.init_app(app)
        except AttributeError:
            pass

    app.sentry = SuperdeskSentry(app)

    return app
