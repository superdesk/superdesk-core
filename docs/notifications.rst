Push Notifications
==================

Superdesk pushes notifications to client via websocket.

Notifications
-------------

``resource:updated``
^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 1.33

Pushed when resource is updated::

    {
        "event": "resource:updated",
        "extra": {
            "resource": "archive",
            "_id": "some-id",
            "fields": {
                "task": 1,
                "task.desk": 1
            }
        }
    }

*Fields* are keys which were changed during the update.

``resource:created``
^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 2.1

Pushed when new resources is created::

    {
        "event": "resource:created",
        "extra": {
            "resource": "archive",
            "_id": "some-id"
        }
    }

``resource:deleted``
^^^^^^^^^^^^^^^^^^^^

.. versionadded:: 2.1

Pushed when resources is deleted::

    {
        "event": "resource:deleted",
        "extra": {
            "resource": "archive",
            "_id": "some-id"
        }
    }
