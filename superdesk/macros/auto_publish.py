# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from quart_babel import gettext as _, lazy_gettext
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE
from superdesk.resource_fields import ID_FIELD


async def auto_publish(item, **kwargs):
    """Publish the item.

    Use it as an on stage macro. Publishing an item that is in transit
    (incoming or outgoing macro) will fail.
    """
    # Only stage rules pass the stage. This blocks direct runs via the macros API,
    # which would skip the publish privilege check.
    if not kwargs.get("stage"):
        raise SuperdeskApiError.forbiddenError(_("Auto Publish can only run as an on stage macro."))

    await get_resource_service("archive_publish").patch_async(
        id=item[ID_FIELD], updates={ITEM_STATE: CONTENT_STATE.PUBLISHED, "auto_publish": True}
    )

    # Refresh the given item in place, so the caller gets the published state and etag.
    published = await get_resource_service("archive").find_one_async(req=None, _id=item[ID_FIELD])
    if published:
        item.update(published)
    return item


name = "Auto Publish"
label = lazy_gettext("Auto Publish")
callback = auto_publish
access_type = "backend"
action_type = "direct"
