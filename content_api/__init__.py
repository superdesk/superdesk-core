# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask import current_app
from .commands import RemoveExpiredItems  # noqa


MONGO_PREFIX = "CONTENTAPI_MONGO"
ELASTIC_PREFIX = "CONTENTAPI_ELASTICSEARCH"


def is_enabled():
    """Test if content api is enabled.

    It can be turned off via ``CONTENTAPI_ENABLED`` setting.
    """
    return current_app.config.get("CONTENTAPI_ENABLED", True)
