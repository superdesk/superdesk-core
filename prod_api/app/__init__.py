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
import importlib

from eve.io.mongo.mongo import MongoJSONEncoder
from eve.render import send_response

from superdesk.flask import Config
from superdesk.datalayer import SuperdeskDataLayer
from superdesk.errors import SuperdeskError, SuperdeskApiError
from superdesk.factory.elastic_apm import setup_apm
from superdesk.validator import SuperdeskValidator
from superdesk.factory.app import SuperdeskEve, set_error_handlers, get_media_storage_class
from superdesk.cache import cache_backend

from prod_api.auth import JWTAuth


def set_prodapi_error_handlers(app):
    """Render errors as ``{"_status": "ERR", "_error": {"code", "message"}}`` like eve and auth errors."""

    @app.errorhandler(SuperdeskError)
    async def prodapi_error_handler(error):
        status_code = error.status_code or 422
        body = {"_status": "ERR", "_error": {"code": status_code, "message": str(error.message or "")}}
        if getattr(error, "payload", None):
            body["_issues"] = error.payload
        return await send_response(None, (body, None, None, status_code))

    @app.errorhandler(500)
    async def prodapi_server_error_handler(error):
        return await prodapi_error_handler(SuperdeskApiError.internalError(error))


def get_app(config=None):
    """
    App factory.

    :param dict config: configuration that can override config
        from `settings.py`
    :return: a new SuperdeskEve app instance
    """

    app_config = Config(".")

    # default config
    app_config.from_object("prod_api.app.settings")

    # https://docs.python-eve.org/en/stable/config.html#domain-configuration
    app_config.update({"DOMAIN": {"upload": {}}})

    # override from instance settings module, but only things defined in default config
    try:
        import settings as server_settings  # type: ignore

        for key in dir(server_settings):
            if key.isupper() and key in app_config:
                app_config[key] = getattr(server_settings, key)
    except ImportError:
        pass

    if config:
        app_config.update(config)

    # media storage
    media_storage = get_media_storage_class(app_config)

    # auth
    auth = None
    if app_config["PRODAPI_AUTH_ENABLED"]:
        auth = JWTAuth

    app = SuperdeskEve(
        auth=auth,
        settings=app_config,
        data=SuperdeskDataLayer,
        media=media_storage,
        json_encoder=MongoJSONEncoder,
        validator=SuperdeskValidator,
    )

    set_error_handlers(app)
    set_prodapi_error_handlers(app)
    setup_apm(app, "Production API")
    cache_backend.init_app(app)

    for module_name in app.config.get("PRODAPI_INSTALLED_APPS", []):
        app_module = importlib.import_module(module_name)
        try:
            init_app = app_module.init_app
        except AttributeError:
            pass
        else:
            init_app(app)

    return app


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "5500"))
    app = get_app()
    app.run(host=host, port=port, debug=True, use_reloader=True)
