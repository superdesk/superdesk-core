NINJS
=====

The schema we use for the ninjs format is an extension of `the standard ninjs schema <http://www.iptc.org/std/ninjs/ninjs-schema_1.1.json>`_.

*Changes from ninjs schema*:

* ``uri`` was replaced by ``guid``: ``uri`` should be the resource identifier on the web but since the item was not published yet it can't be determined at this point
* added ``priority`` field
* added ``service`` field
* added ``slugline`` field
* added ``keywords`` field

Associations dictionary may contain entire items like in this ninjs example: http://dev.iptc.org/ninjs-Examples-3
or just the item ``guid`` and ``type``. In the latest case the items are sent separately before the package item.

Superdesk Schema in :download:`JSON <../superdesk-ninjs-schema.json>`.

.. automodule:: superdesk.publish.formatters.ninjs_formatter
    :members:
