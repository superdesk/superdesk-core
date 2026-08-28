import json

from behave import given, then, when
from behave.api.async_step import async_run_until_complete

from superdesk.tests import get_prefixed_url
from superdesk.tests.http_mocks import CallbackResult, mock_http
from superdesk.tests.steps import apply_placeholders

#: Catalogue the mocked provider answers ``GET /models`` with
PROVIDER_MODELS = ["openai/gpt-4o-mini", "openai/gpt-4o"]

#: Answers the mocked provider completes with, in the JSON contract the prompt asks for
PROVIDER_SUGGESTIONS = [
    "Council votes on budget",
    "Council backs the budget",
    "Budget passes at the council",
]

#: Token counts of every mocked completion, in the OpenAI-compatible spelling
PROVIDER_TOKEN_USAGE = {"prompt_tokens": 42, "completion_tokens": 7}


@given('a mocked AI provider at "{base_url}"')
def step_given_mocked_ai_provider(context, base_url):
    """Answer the two routes of an OpenAI-compatible provider without leaving the process.

    The docstring can carry ``{"models": [...], "suggestions": [...], "status": 500}`` to change
    what the provider answers with.
    """

    options = json.loads(context.text) if context.text else {}
    status = options.get("status", 200)
    models = options.get("models", PROVIDER_MODELS)
    suggestions = options.get("suggestions", PROVIDER_SUGGESTIONS)
    requests = _provider_requests(context)

    def list_models(url, **kwargs):
        requests.append(kwargs)
        return CallbackResult(status=status, payload={"data": [{"id": model} for model in models]})

    def complete(url, **kwargs):
        requests.append(kwargs)
        payload = kwargs.get("json") or {}
        return CallbackResult(
            status=status,
            payload={
                "model": payload.get("model"),
                "choices": [{"message": {"role": "assistant", "content": json.dumps({"suggestions": suggestions})}}],
                "usage": PROVIDER_TOKEN_USAGE,
            },
        )

    http_mock = mock_http(context)
    http_mock.add(f"{base_url}/models", "GET", callback=list_models, repeat=True)
    http_mock.add(f"{base_url}/chat/completions", "POST", callback=complete, repeat=True)


@then('the AI provider was called with the api key "{api_key}"')
def step_then_provider_called_with_api_key(context, api_key):
    authorization = _last_provider_authorization(context)
    assert authorization == f"Bearer {api_key}", "provider was called with %s" % authorization


@then("the AI provider was called with no api key")
def step_then_provider_called_without_api_key(context):
    authorization = _last_provider_authorization(context)
    assert authorization is None, "provider was called with %s" % authorization


@when('we run the AI action at "{url}"')
@async_run_until_complete
async def step_when_we_run_the_ai_action(context, url):
    await _post_to_custom_route(context, url)


@when('we test the AI provider at "{url}"')
@async_run_until_complete
async def step_when_we_test_the_ai_provider(context, url):
    await _post_to_custom_route(context, url)


@when('we patch "{url}" without an etag')
@async_run_until_complete
async def step_when_we_patch_without_an_etag(context, url):
    """PATCH an item without reading it first.

    ``we patch`` reads the item to take the etag from. ``ai_events`` has none, and the client
    reporting an outcome on one holds ``ai``, which is not enough to read the entry it reports on.
    """

    url = apply_placeholders(context, url)
    data = apply_placeholders(context, context.text)
    context.response = await context.client.patch(
        get_prefixed_url(context.app, url), data=data, headers=context.headers
    )


async def _post_to_custom_route(context, url):
    """POST to a route that answers with a plain body rather than with a resource.

    ``we post to`` remembers the answer as the resource the URL names, which needs the ``_status``
    of a resource response. The run and connection test routes answer with neither.
    """

    url = apply_placeholders(context, url)
    data = apply_placeholders(context, context.text) if context.text else "{}"
    context.response = await context.client.post(get_prefixed_url(context.app, url), data=data, headers=context.headers)


def _provider_requests(context):
    """Keyword arguments of every request made to a mocked provider, oldest first"""

    requests = getattr(context, "ai_provider_requests", None)
    if requests is None:
        requests = []
        context.ai_provider_requests = requests

    return requests


def _last_provider_authorization(context):
    requests = _provider_requests(context)
    assert requests, "no request was made to a mocked AI provider"

    return requests[-1].get("headers", {}).get("Authorization")
