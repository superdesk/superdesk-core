# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
A module that provides the Superdesk production API application object and runs
the Superdesk production API.

The API is built using the `Eve framework <http://python-eve.org/>`_ and is
thus essentially just a normal `Flask <http://flask.pocoo.org/>`_ application.
"""

import os
import flask
import importlib

from eve import Eve
from eve.io.mongo.mongo import MongoJSONEncoder

from superdesk.datalayer import SuperdeskDataLayer
from superdesk.storage import SuperdeskGridFSMediaStorage
from superdesk.validator import SuperdeskValidator
from superdesk.factory.app import set_error_handlers
from superdesk.factory.sentry import SuperdeskSentry

from prod_api.auth import JWTAuth


def get_app(config=None):
    """
    App factory.

    :param dict config: configuration that can override config
        from `settings.py`
    :return: a new SuperdeskEve app instance
    """

    app_config = flask.Config(".")

    # default config
    app_config.from_object("prod_api.app.settings")

    # https://docs.python-eve.org/en/stable/config.html#domain-configuration
    app_config.update({"DOMAIN": {"upload": {}}})

    # override from instance settings module, but only things defined in default config
    try:
        import settings as server_settings

        for key in dir(server_settings):
            if key.isupper() and key in app_config:
                app_config[key] = getattr(server_settings, key)
    except ImportError:
        pass

    if config:
        app_config.update(config)

    # media storage
    media_storage = SuperdeskGridFSMediaStorage
    if app_config.get("AMAZON_CONTAINER_NAME"):
        from superdesk.storage import AmazonMediaStorage

        media_storage = AmazonMediaStorage

    # auth
    auth = None
    if app_config["PRODAPI_AUTH_ENABLED"]:
        auth = JWTAuth

    app = Eve(
        auth=auth,
        settings=app_config,
        data=SuperdeskDataLayer,
        media=media_storage,
        json_encoder=MongoJSONEncoder,
        validator=SuperdeskValidator,
    )

    app.notification_client = None

    set_error_handlers(app)

    for module_name in app.config.get("PRODAPI_INSTALLED_APPS", []):
        app_module = importlib.import_module(module_name)
        try:
            init_app = app_module.init_app
        except AttributeError:
            pass
        else:
            init_app(app)

    app.sentry = SuperdeskSentry(app)

    return app


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "5500"))
    app = get_app()
    app.run(host=host, port=port, debug=True, use_reloader=True)
