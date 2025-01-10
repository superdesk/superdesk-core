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
from ..content_types.service import ContentTypesService


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

    def _process_fetched_object(self, doc):
        super()._process_fetched_object(doc)

        profile_id = doc.get("profile")
        if profile_id:
            doc["profile"] = ContentTypesService().get_output_name(profile_id)
