.. _core_config:

Config
======

.. module:: superdesk.core.config

Defining Config Values
----------------------

The values in a config are defined by creating a class that inherits from the :class:`ConfigModel` class.
Define the available fields like you would a `TypedDict`::

    from superdesk.core.config import ConfigModel

    class MyConfig(ConfigModel):
        url: str
        username: str
        password: str


Loading Configs
---------------

You can use the config system to manually load configs on demand. This is used by resource systems, such as mongo,
to load different config options based on a prefix, such as `MONGO` or `CONTENTAPI_MONGO`.

Using the above config model, you can load it using the :func:`get_config_instance` method::

    from typing import Dict, Any
    from superdesk.core.config import get_config_instance

    def test_custom_config():
        # Mock app config
        app_config: Dict[str, Any] = {
            "MY_URL": "localhost:5700",
            "MY_USERNAME": "monkey",
            "MY_PASSWORD": "bars",
        }

        # Get the instance, and assert it's values
        config = get_config_instance(
            app_config,
            MyConfig,
            prefix="MY"
        )
        assert config.url == "localhost:5700"
        assert config.username = "monkey"
        assert config.password = "bars"

        # The following line would raise a pydantic.ValidationError
        # because not all of the required fields of the config
        # would be populated from the supplied app config
        get_config_instance({}, MyConfig, prefix="MY")


You can also load the config from the currently running app config::

    from superdesk.core.app import get_current_app

    def test_config_from_app():
        config = get_config_instance(
            get_current_app().wsgi.config,
            MyConfig,
            prefix="MY"
        )


Validation
----------
Under the hood the ConfigModel uses `Pydantic`. This enables us to use it's validation system
to ensure the config values are correct. If the loading fails, a `pydantic.Validation` exception
will be raised.::

    def test_invalid_configs():
        app_config: Dict[str, Any] = {
            "MY_URL": "localhost:5700",
            "MY_USERNAME": 1234,
        }
        get_config_instance(app_config, MyConfig, prefix="MY")

The above will fail validation because **MY_USERNAME** is the incorrect data type, and **MY_PASSWORD** is missing
from the supplied config.


Config Reference
----------------

.. autofunction:: superdesk.core.config.get_config_key

.. autofunction:: superdesk.core.config.get_config_instance

.. autofunction:: superdesk.core.config.load_config_instance
