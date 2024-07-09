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

Configs must be loaded before they can be used. If you attempt to access a value in a config before it has been
loaded, a `RuntimeError` will be raised. You can load a config in the following 2 days:

* By the :func:`ConfigModel.create_from_dict` class level method, which will create and load a config instance for us
* Or by the :func:`ConfigModel.load_from_dict` instance level method, which will load an already created config instance.

This allows us to manually load configs on demand. This is used by resource systems, such as mongo,
to load different config options based on a prefix, such as `MONGO` or `CONTENTAPI_MONGO`.

The following are examples on how to load a config::

    from typing import Dict, Any

    def test_custom_config():
        # Mock app config
        app_config: Dict[str, Any] = {
            "MY_URL": "localhost:5700",
            "MY_USERNAME": "monkey",
            "MY_PASSWORD": "bars",
        }

        # Using the class level method to create the instance for us
        config = MyConfig.create_from_dict(app_config, prefix="MY")

        # Loading an already constructed config instance
        config = MyConfig()
        config.load_from_dict(app_config, prefix="MY")

        # Get the instance, and assert it's values
        config = MyConfig.create_from_dict(app_config, prefix="MY")
        assert config.url == "localhost:5700"
        assert config.username = "monkey"
        assert config.password = "bars"

        # The following line would raise a pydantic.ValidationError
        # because not all of the required fields of the config
        # would be populated from the supplied app config
        MyConfig.create_from_dict({}, prefix="MY")


You can also load the config from the currently running app config::

    from superdesk.core.app import get_current_async_app

    def test_config_from_app():
        config = MyConfig.create_from_dict(
            get_current_async_app().wsgi.config,
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
        MyConfig.create_from_dict(app_config, prefix="MY")

The above will fail validation because **MY_USERNAME** is the incorrect data type, and **MY_PASSWORD** is missing
from the supplied config.


Config Reference
----------------

.. autoclass:: superdesk.core.config.ConfigModel
    :member-order: bysource
    :members: create_from_dict, load_from_dict

.. autofunction:: superdesk.core.config.get_config_key
