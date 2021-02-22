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

import os
import flask
import importlib

from eve import Eve
from eve.io.mongo.mongo import MongoJSONEncoder

from content_api.tokens import SubscriberTokenAuth
from superdesk.datalayer import SuperdeskDataLayer
from superdesk.validator import SuperdeskValidator
from superdesk.factory.app import set_error_handlers, get_media_storage_class
from superdesk.factory.sentry import SuperdeskSentry


def get_app(config=None):
    """
    App factory.

    :param dict config: configuration that can override config
        from `settings.py`
    :return: a new SuperdeskEve app instance
    """
    app_config = flask.Config(".")

    # get content api default conf
    app_config.from_object("content_api.app.settings")

    # set some required fields
    app_config.update({"DOMAIN": {"upload": {}}, "SOURCES": {}})

    try:
        # override from settings module, but only things defined in default config
        import settings as server_settings  # type: ignore

        for key in dir(server_settings):
            if key.isupper() and key in app_config:
                app_config[key] = getattr(server_settings, key)
    except ImportError:
        pass  # if exists

    if config:
        app_config.update(config)

    media_storage = get_media_storage_class(app_config)

    app = Eve(
        auth=SubscriberTokenAuth,
        settings=app_config,
        data=SuperdeskDataLayer,
        media=media_storage,
        json_encoder=MongoJSONEncoder,
        validator=SuperdeskValidator,
    )

    app.notification_client = None

    set_error_handlers(app)

    for module_name in app.config.get("CONTENTAPI_INSTALLED_APPS", []):
        app_module = importlib.import_module(module_name)
        try:
            app_module.init_app(app)
        except AttributeError:
            pass

    app.sentry = SuperdeskSentry(app)

    return app


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "5400"))
    app = get_app()
    app.run(host=host, port=port, debug=True, use_reloader=True)
