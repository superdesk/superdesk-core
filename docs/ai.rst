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


.. _ai_providers_and_actions:

Language model providers and actions
------------------------------------

The ``superdesk.ai`` module holds the language model providers Superdesk sends content to, the
actions built on them (suggest a headline, summarise an article), and a log of every run.

Three resources make it up:

``ai_providers``
    A service and the credentials to reach it. The POC ships one provider type,
    ``openai_compatible``, which covers OpenAI itself as well as OpenRouter, Azure style gateways
    and local runtimes. ``GET /api/ai_providers/<id>/models`` lists the models a stored provider
    offers and ``POST /api/ai_providers/<id>/test`` reports whether it answers at all.

``ai_actions``
    What to ask for and of which provider: the item fields to send, the field the answers are
    meant for, how many answers and how long they may be.

``ai_events``
    One entry per run, written whether the run succeeded or failed. It holds who ran what, against
    which item, how long it took and how many characters and tokens went each way. The article
    text is never stored, only its size.

Managing providers and actions and reading the log need the ``ai_studio`` privilege. Running an
action and reporting what was done with its answers need ``ai``, which is the right an editor
holds: provider credentials are stored unencrypted, so ``ai_studio`` amounts to access to every
key and belongs to administrators only.

Walkthrough
^^^^^^^^^^^

The four calls below register a provider, add an action for it, run the action against an item and
report what the editor did with the answers. ``$TOKEN`` is a Superdesk session token.

.. code:: sh

    API=http://localhost:5000/api
    AUTH="Authorization: Bearer $TOKEN"
    JSON="Content-Type: application/json"

Register the provider. The key is stored but never returned, by this call or any other:

.. code:: sh

    curl -X POST $API/ai_providers -H "$AUTH" -H "$JSON" -d '{
        "name": "OpenRouter",
        "provider_type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "sk-or-v1-...",
        "default_model": "openai/gpt-4o-mini"
    }'

    {"_id": "68af1c0e2b1a4c0f9a3d1e01", "name": "OpenRouter", "active": true, "_status": "OK", ...}

Add an action for it. ``input_fields`` are read from the item, ``output_field`` is the field the
client writes an accepted answer to:

.. code:: sh

    curl -X POST $API/ai_actions -H "$AUTH" -H "$JSON" -d '{
        "name": "Headline suggestions",
        "action_type": "suggestion",
        "input_fields": ["body_html"],
        "output_field": "headline",
        "suggestions_count": 3,
        "max_characters": 60,
        "provider": "68af1c0e2b1a4c0f9a3d1e01"
    }'

    {"_id": "68af1c0e2b1a4c0f9a3d1e02", "name": "Headline suggestions", "_status": "OK", ...}

Run it against an item. ``fields`` is optional and holds the text as the client currently has it,
which is what an editor with unsaved changes should send; without it the stored item is used. An
answer longer than ``max_characters`` is returned whole and flagged, never cut:

.. code:: sh

    curl -X POST $API/ai_actions/68af1c0e2b1a4c0f9a3d1e02/run -H "$AUTH" -H "$JSON" -d '{
        "item_id": "urn:newsml:localhost:2026-08-27T10:00:00:1234",
        "source": "authoring"
    }'

    {
        "suggestions": [
            {"text": "Council backs the budget", "over_limit": false},
            {"text": "Budget passes after long debate", "over_limit": false},
            {"text": "Councillors vote the budget through", "over_limit": false}
        ],
        "event_id": "68af1c0e2b1a4c0f9a3d1e03",
        "provider": "68af1c0e2b1a4c0f9a3d1e01",
        "model": "gpt-4o-mini-2024-07-18",
        "usage": {"input_tokens": 412, "output_tokens": 37}
    }

Report what happened to the answers, against the ``event_id`` the run returned. ``outcome`` is
``accepted``, ``edited`` or ``discarded``, and ``applied_index`` says which suggestion was taken,
counting from zero. They are the only two fields an update may carry; the time of the report is
stamped by the server. ``pending`` is what an entry holds until somebody reports on it and cannot
be sent back, and ``applied_index`` only goes with ``accepted`` or ``edited``. An outcome can be
reported again, an accepted suggestion that was edited afterwards for instance; reporting
``discarded`` clears the ``applied_index`` an earlier report stored.

Only the user the run was made for may report on it. Holders of ``ai_studio``, who can read the
whole log anyway, may report on any entry. The answer carries the outcome alone: the editor sending
it holds ``ai``, which is not enough to read the entry itself.

.. code:: sh

    curl -X PATCH $API/ai_events/68af1c0e2b1a4c0f9a3d1e03 -H "$AUTH" -H "$JSON" -d '{
        "outcome": "accepted",
        "applied_index": 0
    }'

    {"_id": "68af1c0e2b1a4c0f9a3d1e03", "outcome": "accepted", "applied_index": 0,
     "outcome_at": "2026-08-27T10:00:14+0000"}

Using a provider from code
^^^^^^^^^^^^^^^^^^^^^^^^^^

The provider layer is not tied to the editorial actions. Any server-side feature (a macro, an
automation, a validation step) can send content to a configured provider directly:

.. code:: python

    from superdesk.core import get_current_async_app
    from superdesk.ai.providers import get_client
    from superdesk.ai.providers.base import CompletionMessage, CompletionRequest

    providers = get_current_async_app().resources.get_resource_service("ai_providers")
    provider = await providers.find_by_id(provider_id)

    result = await get_client(provider).complete(
        CompletionRequest(
            model=provider.default_model,
            messages=[CompletionMessage(role="user", content="Summarise: ...")],
        )
    )
    result.content, result.input_tokens, result.output_tokens

Failures raise ``AIProviderError`` with a ``kind`` (``auth``, ``rate_limit``, ``timeout``,
``upstream``, ``invalid_response``); the request timeout comes from ``AI_REQUEST_TIMEOUT``. The
call is async only.

Two conventions for new callers: keep the call server side, the browser never talks to a model
directly, and write an ``ai_events`` entry with your own ``source`` value so the usage shows up
next to the editorial actions in the log.
