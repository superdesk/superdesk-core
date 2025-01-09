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
import superdesk


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
        self._add_content_profile_name(doc)

    def _add_content_profile_name(self, doc):
        """
        Adds the `profile_name` field to the item document based on the profile ID.
        """
        profile_id = doc.get("profile")

        if profile_id:
            content_profile_name = self._get_profile_name(profile_id)
            doc["profile_name"] = content_profile_name

    def _get_profile_name(self, profile_id):
        """
        Fetch the profile name based on the profile ID

        """
        content_types_service = superdesk.get_resource_service("content_types")
        profile = content_types_service.find_one(req=None, _id=profile_id)
        if profile:
            return profile.get("label", "")
        else:
            return ""
