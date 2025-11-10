# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import date, timedelta, time
from typing import Dict, Tuple, TypedDict
from superdesk import get_resource_service
from superdesk.eve_async import AsyncListCursor
from ..service import ProdApiService


class AvailabilityData(TypedDict):
    status: str
    published_articles: int
    published_events: int
    working_hours: list[dict[str, str]]


AvailabilityMap = Dict[str, AvailabilityData]


def format_hours(availability_day):
    def format_time(t):
        # Converts 'HH:MM:SS' or 'HH:MM' to 'HH:MM'
        if not t or not isinstance(t, str):
            # Handle None and non-string inputs
            return ""
        try:
            return time.fromisoformat(t).strftime("%H:%M")
        except ValueError:
            return t[:5] if len(t) >= 5 else t

    if availability_day.get("working_hours"):
        hours = [
            {"start": format_time(wh["start_time"]), "end": format_time(wh["end_time"])}
            for wh in availability_day["working_hours"]
            if wh.get("start_time") and wh.get("end_time")
        ]
        return sorted(hours, key=lambda wh: wh["start"])
    return []


class UserAvailabilityService(ProdApiService):
    """Service class for the user availability endpoint in Production API."""

    excluded_fields = {
        "_generated",
    } | ProdApiService.excluded_fields

    async def get_async(self, req, lookup):
        start_date, end_date = self.get_start_end_dates(req)
        availability_enabled = [
            default_availability["_id"]
            for default_availability in get_resource_service("default_user_availability").get_from_mongo(
                req=None, lookup={"enabled": True}, projection={"_id": 1}
            )
        ]
        users = await get_resource_service("users").find_async(
            where={"_id": {"$in": availability_enabled}, "is_active": True}
        )
        user_data = [self._get_user_availability(user, start_date, end_date) async for user in users]
        return AsyncListCursor(user_data)

    async def find_one_async(self, req, **lookup):
        start_date, end_date = self.get_start_end_dates(req)
        user = await get_resource_service("users").find_one_async(req=None, **lookup)
        if not user:
            return user
        user_data = self._get_user_availability(user, start_date, end_date)
        user_data["_links"] = {}
        return user_data

    def get_start_end_dates(self, req) -> Tuple[date, date]:
        """Get the start and end dates for the availability data."""
        today = date.today()
        if req:
            if req.args.get("day"):
                year, month, day = map(int, req.args.get("day").split("-"))
                start_date = date(year, month, day)
                end_date = start_date + timedelta(days=1)
                return start_date, end_date

            elif req.args.get("month"):
                year, month = map(int, req.args.get("month").split("-"))
                start_date = date(year, month, 1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
                if end_date > today:
                    end_date = today + timedelta(days=1)
                return start_date, end_date

        start_date = date(today.year, today.month, 1)
        end_date = today + timedelta(days=1)
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
