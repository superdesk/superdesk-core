.. _architecture:

Architecture
============
Here there is info about main components in Superdesk and how these interact.
To run superdesk we use `honcho <https://github.com/nickstenning/honcho>`_ to define
processes for each of components::

    rest: gunicorn -c gunicorn_config.py wsgi
    wamp: python3 -u ws.py
    work: celery -A worker worker
    beat: celery -A worker beat --pid=

REST API Server
---------------
The entry point is Superdesk REST API. This is a python application built on top of `eve <http://python-eve.org/>`_ and `flask <http://flask.pocoo.org/>`_ frameworks.
Clients communicate with this api to authenticate, fetch and modify data, upload new content etc.

There is an app factory which you can use to create apps for production/testing:

.. autofunction:: superdesk.factory.get_app

It can use different wsgi servers, we use `Gunicorn <http://gunicorn.org/>`_.

Notifications
-------------
There is also websockets server where both API server and celery workers can push
notifications to clients, which use that information to refresh views or
otherwise keep in sync. In the background it's using celery queue and from there
it sends everything to clients. There is no communication from client to server,
all changes are done via API server.

There is also a factory to create notification server:

.. autofunction:: superdesk.ws.create_server

Celery Workers
--------------
Tasks that involve communication with external services (ingest update, publishing), do some binary files manipulation (image cropping, file metadata extraction) or happen periodically (content expiry) are executed using `celery <http://www.celeryproject.org/>`_.

It uses same app factory like API server.

Data Layer
----------
In short - main data storage is `mongoDB <https://www.mongodb.com/>`_, content items are also indexed using `elastic <https://www.elastic.co/products/elasticsearch>`_. This logic is implemented via custom eve data layer, superdesk service layer and data backend.

.. autoclass:: superdesk.datalayer.SuperdeskDataLayer
    :members:

.. autoclass:: superdesk.services.BaseService
    :members:

.. autoclass:: superdesk.eve_backend.EveBackend
    :members:

Media Storage
--------------
By default uploaded/ingested files are stored in `mongoDB GridFS <https://docs.mongodb.com/manual/core/gridfs/>`_.

.. autoclass:: superdesk.storage.SuperdeskGridFSMediaStorage
    :members:

There is also Amazon S3 implementation, which is used when Amazon is configured via settings.

.. autoclass:: superdesk.storage.AmazonMediaStorage
    :members:
