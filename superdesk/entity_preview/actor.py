# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from superdesk import get_resource_service
from superdesk.flask import g


logger = logging.getLogger(__name__)

_MISSING = object()


@asynccontextmanager
async def actor_context(user: dict) -> AsyncIterator[dict]:
    """Run a block as if the given user had made the request.

    Populates ``g.user`` and ``g.role`` the same way ``set_user_request_auth_data`` does for a real
    request, so anything reading the current user (privilege checks, the archive and search filters)
    sees this user. ``invisible_stages`` is resolved up front because the filters prefer it over a
    lookup. Previous values are restored on exit, so this can be used inside a real request too.
    """

    users_service: Any = get_resource_service("users")
    role = await users_service.get_role(user)
    users_service.set_privileges(user, role)
    user["invisible_stages"] = await users_service.get_invisible_stages_ids_async(user["_id"])

    previous_user = getattr(g, "user", _MISSING)
    previous_role = getattr(g, "role", _MISSING)
    g.user = user
    g.role = role

    try:
        yield user
    finally:
        _restore(g, "user", previous_user)
        _restore(g, "role", previous_role)


def _restore(ctx: Any, name: str, value: Any) -> None:
    if value is _MISSING:
        try:
            delattr(ctx, name)
        except AttributeError:
            pass
    else:
        setattr(ctx, name, value)
