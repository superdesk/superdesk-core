.. core_modules:

Modules
=======

.. module:: superdesk.core

Loading Modules
---------------

The :class:`Module <module.Module>` class is used to register modules with the system, and provides attributes
used to define certain behaviour of the module.

An example of a module's root file::

    # file: my/module/__init__py
    from superdesk.core.module import Module, SuperdeskAsyncApp

    def init(app: SuperdeskAsyncApp):
        ...

    module = Module(
        name="my.module",
        init=init,
        frozen=True,
        priority=100
    )

Then you would add the following to your :ref:`settings.modules` config::

    # file: settings.py
    MODULES = ["my.module"]

The system would then load this module when the application starts

Module Loading Sequence
-----------------------

The :class:`SuperdeskAsyncApp <superdesk.core.app.SuperdeskAsyncApp>` app is in charge of loading modules,
when the `start` function is run on the app.

Modules are loaded in the following 3 stages.

1. Import python module
2. Load module local configs
3. Run module init functions

The app will import ALL modules first, then ALL module configs are loaded, then ALL module init functions are run.
This way we can ensure that all python modules and configs are loaded **before** initialising the modules themself.

Module Configuration
--------------------

A module can optionally have a :ref:`config <core_config>` loaded on app startup. This can be achieved by setting config options on the Module
instance.::

    # file: my/module/__init__py
    from typing import Optional, Dict, Any

    from superdesk.core.module import Module, SuperdeskAsyncApp
    from superdesk.core.config import ConfigModel


    # Create a new Config class that inherits from `ConfigModel`
    class ModuleConfig(ConfigModel):
        # Make sure to provide defaults for all fields
        # otherwise validation would fail
        uri: str = "localhost"
        port: int = 27017
        options: Optional[Dict[str, Any]] = None

    # Create a module local instance of the class,
    # to be used at runtime
    config = ModuleConfig()


    def init(app: SuperdeskAsyncApp):
        # The module's config is loaded BEFORE executing the
        # modules `init` function
        if config.uri == "localhost":
            print("Using a local instance")
        else:
            print("Using a remote instance")

        # You can also import configs from other modules
        # all configs are loaded BEFORE executing module's
        # init function
        from my import module_b
        if module_b.config.enabled:
            print("Secondary module is enabled")
        else:
            print("Secondary module is NOT enabled")


    module = Module(
        name="my.module",
        init=init,
        frozen=True,
        priority=100,

        # Tells the module loading system to load our config for us
        config=config,

        # Optionally use a prefix when loading config values
        config_prefix="MONGO",

        # Optionally tell the module loading system
        # NOT to freeze our config so it can be changed at runtime
        freeze=False,
    )


When the app loads the module, it will populate the values in the config based on attributes from `settings.py`.
For example, the following::

    MONGO_URI = "remote_host.com"
    MONGO_PORT = 37017
    MONGO_OPTIONS = {"w": 3}

is the same as::

    ModuleConfig(
        uri="remote_host.com",
        port=37017,
        options=dict(w=3)
    )

Validation will also occur when loading the module config, so if the value in `settings.py` is invalid with regards
to the ConfigModel used, then the app will refuse to load and throw an error, such as::

    pydantic_core._pydantic_core.ValidationError: 1 validation error for ModuleConfig
    port
      Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='val', input_type=str]
        For further information visit https://errors.pydantic.dev/2.7/v/int_parsing

Module Reference
----------------
.. autoclass:: superdesk.core.module::Module
    :member-order: bysource
    :members:
