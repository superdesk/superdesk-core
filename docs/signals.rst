.. _signals:

Signals in Superdesk
====================

We use `Flask signals <http://flask.pocoo.org/docs/1.0/signals/>`_ to allow custom development on Superdesk.

Usage::

    from superdesk import item_update


    def my_item_update_handler(sender, item, **kwargs):
        print('item updated', item)


    def init_app(app):

        item_update.connect(my_item_update_handler)

Core Signals
------------

.. automodule:: superdesk.signals

.. autodata:: item_update
    :annotation:

.. autodata:: item_updated
    :annotation:

.. autodata:: item_publish
    :annotation:

.. autodata:: item_published
    :annotation:

.. autodata:: item_fetched
    :annotation:

.. autodata:: item_move
    :annotation:

.. autodata:: item_moved
    :annotation:

.. autodata:: item_rewrite
    :annotation:

.. autodata:: item_validate
    :annotation:

.. autodata:: item_duplicate
    :annotation:

.. autodata:: item_duplicated
    :annotation:

.. autodata:: archived_item_removed
    :annotation:

