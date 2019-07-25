.. _spellchecking:

Spellchecking
=============

Superdesk can support several spellcheckers. They are implemented as backend plugin and
used by the client.

Getting list of spellcheckers
-----------------------------
To retrieve list of registered spellcheckers, a GET request must be done on ``spellcheckers_list`` endpoint.

Checking a text
---------------

A text can be checked using ``spellchecker`` endpoint.

.. autoclass:: superdesk.text_checkers.spellcheckers.SpellcheckerService

Getting suggestions
-------------------

Getting suggestions for a word is done in a similar way as checking a text, on the same
``spellchecker`` endpoint, but with the additional ``"suggestions": true`` key.

Spellchecker plugin
-------------------

So far, Superdesk supports the following spellcheckers:


.. autoclass:: superdesk.text_checkers.spellcheckers.grammalecte.Grammalecte

.. autoclass:: superdesk.text_checkers.spellcheckers.leuven_dutch.LeuvenDutch

.. autoclass:: superdesk.text_checkers.spellcheckers.default.Default
