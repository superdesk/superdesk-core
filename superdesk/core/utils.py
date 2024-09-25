# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import cast
from datetime import datetime
from uuid import uuid4

from .app import get_app_config

GUID_TAG = "tag"
GUID_NEWSML = "newsml"


def generate_guid(**hints) -> str:
    """Generate a GUID based on given hints

    param: hints: hints used for generating the guid
    """
    newsml_guid_format = "urn:newsml:%(domain)s:%(timestamp)s:%(identifier)s"
    tag_guid_format = "tag:%(domain)s:%(year)d:%(identifier)s"

    if not hints.get("id"):
        hints["id"] = str(uuid4())

    def get_conf(key: str, default: bool | str) -> bool | str:
        try:
            return cast(bool | str, get_app_config(key, default))
        except RuntimeError:
            return default

    try:
        if get_conf("GENERATE_SHORT_GUID", False):
            return hints["id"]
    except RuntimeError:
        # This occurs when attempting to generate an ID when app isn't running
        # No need to bail out, just continue on assuming GENERATE_SHORT_GUID is False
        pass

    t = datetime.today()

    if hints["type"].lower() == GUID_TAG:
        return tag_guid_format % {
            "domain": get_conf("URN_DOMAIN", "localhost"),
            "year": t.year,
            "identifier": hints["id"],
        }

    return newsml_guid_format % {
        "domain": get_conf("URN_DOMAIN", "localhost"),
        "timestamp": t.isoformat(),
        "identifier": hints["id"],
    }
