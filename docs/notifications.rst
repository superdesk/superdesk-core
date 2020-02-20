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
