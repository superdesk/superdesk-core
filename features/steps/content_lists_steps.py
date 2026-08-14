import json
import re

from behave import given, when, then, step
from behave.api.async_step import async_run_until_complete

from superdesk.core import get_current_async_app
from superdesk.tests import get_prefixed_url, set_placeholder
from superdesk.tests.http_mocks import mock_http
from superdesk.tests.steps import apply_placeholders, get_resource_name, get_json_data, json_match

from apps.content_lists.webhooks import ContentListWebhooksService


async def _insert_archive_item(item_id, extra=None):
    """Insert a minimal archive document directly into MongoDB.

    Avoids archive service validation complexity while satisfying the
    validate_data_relation_async("archive") check on ContentListItem.content.
    """
    doc = {"_id": item_id, "guid": item_id, "type": "text"}
    if extra:
        doc.update(extra)
    async_app = get_current_async_app()
    collection = async_app.mongo.get_collection_async("archive")
    await collection.insert_one(doc)


@given('an archive item "{item_id}"')
@async_run_until_complete
async def step_given_archive_item(context, item_id):
    await _insert_archive_item(item_id)


@given('an archive item "{item_id}" with data')
@async_run_until_complete
async def step_given_archive_item_with_data(context, item_id):
    """Insert an archive document with extra fields taken from the docstring."""
    await _insert_archive_item(item_id, json.loads(context.text))


@when('we bulk patch items for "{url}"')
@async_run_until_complete
async def step_bulk_patch_items_for(context, url):
    """PATCH the content list items endpoint without an If-Match header.

    The bulk update endpoint uses updatedAt in the payload for concurrency
    control rather than the standard etag header.
    """
    url = apply_placeholders(context, url)
    data = apply_placeholders(context, context.text)
    context.response = await context.client.patch(
        get_prefixed_url(context.app, url), data=data, headers=context.headers
    )
    if context.response.status_code in (200, 201):
        item = json.loads(await context.response.get_data())
        if item.get("_id"):
            resource = get_resource_name(url)
            _store(context, resource, item)


@step('we store response as "{resource}"')
@async_run_until_complete
async def step_store_response_as(context, resource):
    """Store the current response body as a named placeholder.

    Useful after a GET or custom endpoint call to make fields available
    for use in subsequent steps as #resource.field# placeholders.
    """
    item = await get_json_data(context.response)
    _store(context, resource, item)


def _store(context, name, item):
    """Mirror the storage pattern used by store_placeholder in core steps."""
    setattr(context, name, item)
    set_placeholder(context, name, item)


#
# Webhook delivery steps.
#
# Celery runs eagerly under behave (``update_config`` in superdesk/tests/__init__.py),
# so a delivery has already been POSTed by the time the triggering API call returns.
# ``mock_http`` intercepts it, the same way the http_push feature asserts publishing.
#


def _register_endpoint(context, url, status=200):
    """Intercept POSTs to ``url`` and remember it as a webhook target.

    Matching is done with a pattern rather than the literal URL because the
    webhook model canonicalizes ``url`` (a bare domain gains a trailing slash),
    so the URL we register here and the one actually called can differ.
    """
    mock_http(context).post(re.compile("^" + re.escape(url.rstrip("/")) + "/?$"), status=status, repeat=True)
    if not hasattr(context, "webhook_endpoints"):
        context.webhook_endpoints = set()
    context.webhook_endpoints.add(url.rstrip("/"))


def _webhook_calls(context):
    """Return [(url, decoded payload)] for deliveries to registered endpoints."""
    calls = []
    endpoints = getattr(context, "webhook_endpoints", set())
    for (method, url), request_calls in mock_http(context).requests.items():
        if method != "POST" or str(url).rstrip("/") not in endpoints:
            continue
        for request_call in request_calls:
            calls.append((str(url).rstrip("/"), json.loads(request_call.kwargs["data"])))
    return calls


@step('a mocked http endpoint at "{url}"')
def step_mocked_http_endpoint(context, url):
    """Accept POSTs to a URL without registering a webhook for it.

    For scenarios that create the webhook themselves, to control ``enabled``
    or ``excluded_lists``.
    """
    _register_endpoint(context, url)


@given('a webhook endpoint at "{url}"')
@async_run_until_complete
async def step_given_webhook_endpoint(context, url):
    """Register an enabled webhook pointing at a URL that accepts deliveries."""
    _register_endpoint(context, url)
    async with context.app.app_context():
        await ContentListWebhooksService().create([{"url": url, "enabled": True}])


@given('a failing webhook endpoint at "{url}"')
@async_run_until_complete
async def step_given_failing_webhook_endpoint(context, url):
    """Register an enabled webhook whose endpoint always answers 500."""
    _register_endpoint(context, url, status=500)
    async with context.app.app_context():
        await ContentListWebhooksService().create([{"url": url, "enabled": True}])


@when("we reset webhook deliveries")
def step_reset_webhook_deliveries(context):
    """Forget deliveries recorded so far.

    Creating a content list fires ``content_list:created`` on its own, so a
    scenario asserting on a later event must clear first.
    """
    mock_http(context).requests.clear()


@then("we delivered {count:d} webhook")
@then("we delivered {count:d} webhooks")
def step_we_delivered_webhooks(context, count):
    calls = _webhook_calls(context)
    assert len(calls) == count, "expected %d deliveries, got %d: %s" % (count, len(calls), calls)

    if context.text:
        expected = json.loads(apply_placeholders(context, context.text))
        payloads = [payload for _, payload in calls]
        assert json_match(expected, payloads), "%s\n != \n%s" % (expected, payloads)

    mock_http(context).requests.clear()


@then('we delivered {count:d} webhook to "{url}"')
@then('we delivered {count:d} webhooks to "{url}"')
def step_we_delivered_webhooks_to(context, count, url):
    """Assert per-endpoint delivery counts.

    Unlike the step above this does not clear the recorded deliveries, so a
    scenario can assert on several endpoints in turn.
    """
    calls = [call for call in _webhook_calls(context) if call[0] == url.rstrip("/")]
    assert len(calls) == count, "expected %d deliveries to %s, got %d" % (count, url, len(calls))

    if context.text:
        expected = json.loads(apply_placeholders(context, context.text))
        payloads = [payload for _, payload in calls]
        assert json_match(expected, payloads), "%s\n != \n%s" % (expected, payloads)
