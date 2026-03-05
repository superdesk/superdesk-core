import json

from behave import given, when, step
from behave.api.async_step import async_run_until_complete

from superdesk.core import get_current_async_app
from superdesk.tests import get_prefixed_url, set_placeholder
from superdesk.tests.steps import apply_placeholders, get_resource_name, get_json_data


@given('an archive item "{item_id}"')
@async_run_until_complete
async def step_given_archive_item(context, item_id):
    """Insert a minimal archive document directly into MongoDB.

    Avoids archive service validation complexity while satisfying the
    validate_data_relation_async("archive") check on ContentListItem.content.
    """
    async_app = get_current_async_app()
    collection = async_app.mongo.get_collection_async("archive")
    await collection.insert_one({"_id": item_id, "guid": item_id, "type": "text"})


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
