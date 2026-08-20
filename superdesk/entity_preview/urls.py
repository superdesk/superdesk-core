# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.core import get_app_config


def get_client_url() -> str:
    """Base URL of the Superdesk client, without a trailing slash."""

    client_url = get_app_config("CLIENT_URL") or ""
    return client_url.rstrip("/") if isinstance(client_url, str) else ""


def get_item_url(item_id: str) -> str:
    """Client URL of a content item.

    Same shape core itself emits for item notifications, see
    ``ArchiveService.notify_user_on_mark_action`` in ``apps/archive/archive.py``.
    """

    return "{}/#/workspace?item={}&action=view".format(get_client_url(), item_id)
