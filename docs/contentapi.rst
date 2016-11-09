Content API
===========

.. versionchanged:: 1.5

There is a major refactoring ongoing for Content API. Major changes are:

- Less configuration
    it will publish to content api without additional config on subscriber side

- Better integration
    simplified install, no need to clone another repository, just another process

- Supports ``JSON`` only
    dropping ``XML`` support

- Re-uses Superdesk media storage
    there is no duplication of binaries

- Auth everywhere
    avoiding some extra resources which were without authentication

Configuration
-------------

There are a few settings required for Content API to work:

``CONTENT_API_ENABLED``

default: ``True``

``SECRET_KEY``

default: ``''``

used to generate and validate auth tokens

Running Content API
-------------------

You can use :mod:`content_api.wsgi` module in ``Procfile``::

    capi: gunicorn -b 0.0.0.0:$PORT content_api.wsgi
