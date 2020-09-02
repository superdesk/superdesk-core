.. _ai_services:

AI/Machine Learning Services
=================================================

Superdesk can interact with service analysing article using machine learning.

Analyzing an article
--------------------

A text can be analyzed using following endpoint:

.. autodata:: superdesk.text_checkers.ai.AI_SERVICE_ENDPOINT

.. autoclass:: superdesk.text_checkers.ai.AIService


Manipulating service data
-------------------------

Various data of the services may need to be manipulated, this is done following endpoint:

.. autodata:: superdesk.text_checkers.ai.AI_DATA_OP_ENDPOINT

.. autoclass:: superdesk.text_checkers.ai.AIDataOpService


AI services
-----------

So far, Superdesk supports the following AI Services:


.. autoclass:: superdesk.text_checkers.ai.imatrics.IMatrics
