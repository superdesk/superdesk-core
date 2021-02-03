# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from ..service import ProdApiService


class ItemsService(ProdApiService):
    excluded_fields = {
        "fields_meta",
        "unique_id",
        "family_id",
        "event_id",
        "lock_session",
        "lock_action",
        "lock_time",
        "lock_user",
    } | ProdApiService.excluded_fields
