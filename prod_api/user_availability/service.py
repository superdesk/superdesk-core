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
from typing import Tuple
from superdesk import get_resource_service
from superdesk.utils import ListCursor
from ..service import ProdApiService


class UserAvailabilityService(ProdApiService):
    """Service class for the user availability endpoint in Production API."""

    excluded_fields = {
        "_generated",
    } | ProdApiService.excluded_fields

    def get(self, req, lookup):
        start_date, end_date = self.get_start_end_dates(req)
        users = get_resource_service("users").find(where={"is_active": True})
        user_data = [self._get_user_availability(user, start_date, end_date) for user in users]
        return ListCursor(user_data)

    def find_one(self, req, **lookup):
        start_date, end_date = self.get_start_end_dates(req)
        user = get_resource_service("users").find_one(req=None, **lookup)
        if not user:
            raise ValueError("User not found")
        user_data = self._get_user_availability(user, start_date, end_date)
        user_data["_links"] = {}
        return user_data

    def get_start_end_dates(self, req) -> Tuple[date, date]:
        """Get the start and end dates for the availability data."""
        today = date.today()
        if req and req.args.get("month"):
            year, month = req.args.get("month").split("-")
        else:
            year = today.year
            month = today.month
        start_date = date(int(year), int(month), 1)
        end_date = (start_date + timedelta(days=31)).replace(day=1)
        if end_date > today:
            end_date = today
        return start_date, end_date

    def _get_user_availability(self, user, start_date, end_date):
        user_data = {"_id": user["_id"], "username": user["username"], "availability": []}
        availability = {}

        availability_days = self.find(
            where={
                "user": user["_id"],
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lt": end_date.strftime("%Y-%m-%d"),
                },
            }
        )

        for availability_day in availability_days:
            if availability_day.get("status"):
                availability[availability_day["date"]] = {
                    "status": availability_day["status"],
                    "published_articles": 0,
                    "published_events": 0,
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
            availability.setdefault(metric["date"], {"status": "", "published_articles": 0, "published_events": 0})[
                metric["name"]
            ] = metric["value"]

        user_data["availability"] = [
            {
                "date": date,
                "status": availability[date]["status"],
                "published_articles": availability[date]["published_articles"],
                "published_events": availability[date]["published_events"],
            }
            for date in sorted(availability.keys())
        ]

        return user_data
