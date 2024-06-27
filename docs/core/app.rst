.. core_app:

App
===

Getting App Instance
--------------------

The :class:`SuperdeskAsyncApp <app.SuperdeskAsyncApp>` app is built for us automatically in the `SuperdeskEve` app.
You can retrieve an instance of this app from the :meth:`get_current_app <app.get_current_app>` method.::

    from superdesk.core.app import get_current_app

    def test():
        get_current_app().get_module_list()


APP References
--------------

.. autofunction:: superdesk.core.app.get_current_app

.. autoclass:: superdesk.core.app.SuperdeskAsyncApp
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.wsgi.WSGIApp
    :member-order: bysource
    :members:
    :undoc-members:
