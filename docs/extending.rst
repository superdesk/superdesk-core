Extending Superdesk
===================

.. versionchanged:: 1.6

Adding new Search Provider
--------------------------

.. module:: superdesk

You have to implement a new :class:`SearchProvider` and register it within superdesk::

    import superdesk


    class FooSearchProvider(superdesk.SearchProvider):

        label = 'Foo'

        def find(self, query):
            return [{'headline': 'Static list'}]


    def init_app(app):
        superdesk.register_search_provider('foo', provider_class=FooSearchProvider)

This way it will add a new option to subscribers settings.

.. important::
    Don't forget to add such module into :ref:`settings.installed_apps`.

Search Provider API
^^^^^^^^^^^^^^^^^^^

.. autoclass:: SearchProvider
    :members:
