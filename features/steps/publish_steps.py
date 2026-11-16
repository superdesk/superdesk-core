# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import asyncio

from behave import when

from superdesk import json
from superdesk.tests import get_prefixed_url
from superdesk.tests.publish_steps import *  # noqa
from superdesk.tests.steps import apply_placeholders, async_run_until_complete, get_res, if_match


@when('we concurrently schedule "{item_id}"')
@async_run_until_complete
async def concurrently_schedule(context, item_id):
    item_id = apply_placeholders(context, item_id)
    item = await get_res("/archive/" + item_id, context)
    headers = if_match(context, item["_etag"])
    data = json.dumps({"state": "published", **json.loads(apply_placeholders(context, context.text))})
    url = get_prefixed_url(context.app, f"/archive/publish/{item_id}")
    responses = await asyncio.gather(*(context.client.patch(url, data=data, headers=headers) for _ in range(2)))
    statuses = sorted(response.status_code for response in responses)
    assert statuses[0] == 200 and statuses[1] in (400, 409, 412), statuses
