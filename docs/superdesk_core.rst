.. superdesk_core:

New Core Framework
==================
This is the new core application framework, starting from v3.0 onwards.

Modules
-------

.. module:: superdesk.core.module

The :class:`Module` class is used to register modules with the system, and provides attributes
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

Then you would add the following to your `MODULES` config::

    # file: settings.py
    MODULES = ["my.module"]

The system would then load this module when the application starts

.. autoclass:: superdesk.core.module::Module
    :member-order: bysource
    :members:

App
---
.. autoclass:: superdesk.core.app.SuperdeskAsyncApp
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.wsgi.WSGIApp
    :member-order: bysource
    :members:
    :undoc-members:
