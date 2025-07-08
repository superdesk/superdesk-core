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
from typing import Dict, Tuple, TypedDict
from superdesk import get_resource_service
from superdesk.utils import ListCursor
from ..service import ProdApiService


class AvailabilityData(TypedDict):
    status: str
    published_articles: int
    published_events: int
    working_hours: list[dict[str, str]]


AvailabilityMap = Dict[str, AvailabilityData]


def format_hours(availability_day):
    if availability_day.get("working_hours"):
        sorted_hours = sorted(availability_day["working_hours"], key=lambda wh: wh["start_time"])
        return [{"start": wh["start_time"], "end": wh["end_time"]} for wh in sorted_hours]
    return []


class UserAvailabilityService(ProdApiService):
    """Service class for the user availability endpoint in Production API."""

    excluded_fields = {
        "_generated",
    } | ProdApiService.excluded_fields

    def get(self, req, lookup):
        start_date, end_date = self.get_start_end_dates(req)
        availability_enabled = [
            default_availability["_id"]
            for default_availability in get_resource_service("default_user_availability").get_from_mongo(
                req=None, lookup={"enabled": True}, projection={"_id": 1}
            )
        ]
        users = get_resource_service("users").find(where={"_id": {"$in": availability_enabled}})
        user_data = [self._get_user_availability(user, start_date, end_date) for user in users]
        return ListCursor(user_data)

    def find_one(self, req, **lookup):
        start_date, end_date = self.get_start_end_dates(req)
        user = get_resource_service("users").find_one(req=None, **lookup)
        if not user:
            return user
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
        availability_map: AvailabilityMap = {}

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
                availability_map[availability_day["date"]] = {
                    "status": availability_day["status"],
                    "published_articles": 0,
                    "published_events": 0,
                    "working_hours": format_hours(availability_day),
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
            availability_map.setdefault(
                metric["date"], {"status": "", "published_articles": 0, "published_events": 0, "working_hours": []}
            )[metric["name"]] = metric["value"]

        user_data["availability"] = [
            {
                "date": date,
                "status": availability_map[date]["status"],
                "published_articles": availability_map[date]["published_articles"],
                "published_events": availability_map[date]["published_events"],
                "working_hours": availability_map[date]["working_hours"],
            }
            for date in sorted(availability_map.keys())
        ]

        return user_data
