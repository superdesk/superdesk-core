.. _cache:

Caching
=======

.. versionadded:: 1.3

There is a Superdesk wrapper for `Hermes cache <https://pypi.python.org/pypi/HermesCache>`_.

Basic usage is::

    from superdesk.cache import cache 

    @cache(ttl=30)
    def some_func(foo):
        return foo * 5


    class Service():
    
        @cache(ttl=50)
        def foo(self):
            return

Cache providers
---------------

Redis
^^^^^

This one is enabled by default, using ``REDIS_URL`` for config.

Memcached
^^^^^^^^^

In order to use memcached:
  - install ``python3-memcached`` library
  - set ``SUPERDESK_CACHE_URL`` env var to your memcached instance,
    or set it via ``CACHE_URL`` in settings.

App Context
"""""""""""

It requires ``flask.app`` for the config, you can still annotate methods/functions before the app is created,
but you can not call these methods before there is an app context in place.

Serialization
"""""""""""""

Cache handles superdesk data encoding/decoding so you will get ``datetime`` and ``ObjectId`` instances.
However, it doesn't handle yet more complex types - like ``Cursor`` objects returned after mongo/elastic queries::

    @cache(ttl=50)
    def return_from_db():
        return get_resource_service('foo').get()

Will raise an error. What you can do instead::

    @cache(ttl=50)
    def return_from_db():
        return [doc for doc in get_resource_service('foo').get()]

