# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import date, timedelta
from superdesk import get_resource_service
from superdesk.utils import ListCursor
from ..service import ProdApiService


class UserAvailabilityService(ProdApiService):
    """Service class for the user availability endpoint in Production API."""

    excluded_fields = {
        "_generated",
    } | ProdApiService.excluded_fields

    def get(self, req, lookup):
        today = date.today()
        if req and req.args.get("month"):
            year, month = req.args.get("month").split("-")
        else:
            year = today.year
            month = today.month
        start_date = date(int(year), int(month), 1)
        end_date = (start_date + timedelta(days=31)).replace(day=1)
        today = date.today()
        if end_date > today:
            end_date = today
        users = get_resource_service("users").find(where={"is_active": True})
        user_data = [self._get_user_availability(user, start_date, end_date) for user in users]

        return ListCursor(user_data)

    def _get_user_availability(self, user, start_date, end_date):
        user_data = {"username": user["username"], "availability": {}}

        availability = self.find(
            where={
                "user": user["_id"],
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lt": end_date.strftime("%Y-%m-%d"),
                },
            }
        )

        for day_availability in availability:
            if day_availability.get("status"):
                user_data["availability"][day_availability["date"]] = {
                    "status": day_availability["status"],
                }

        metrics = get_resource_service("user_metrics").find(
            where={
                "user": user["_id"],
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lt": end_date.strftime("%Y-%m-%d"),
                },
            }
        )

        for metric in metrics:
            user_data["availability"].setdefault(metric["date"], {"status": ""})[metric["name"]] = metric["value"]

        return user_data
