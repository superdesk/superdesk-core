# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import pytz
from datetime import datetime, timedelta

from apps.rules.routing_rules import Weekdays
from apps.templates.content_templates import get_next_run, get_item_from_template, render_content_template
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE
from superdesk.tests import TestCase
from superdesk.utc import utcnow


class TemplatesTestCase(TestCase):
    def setUp(self):
        # now is today at 09:05:03
        self.now = datetime.utcnow().replace(hour=9, minute=5, second=3)
        self.weekdays = [day.name for day in Weekdays]

    def get_delta(self, create_at, weekdays, time_zone=None, now=None, cron_list=None):
        schedule = {"day_of_week": weekdays, "create_at": create_at, "is_active": True, "time_zone": time_zone or "UTC"}
        if cron_list:
            schedule["cron_list"] = cron_list
            schedule.pop("create_at", None)

        next_run = get_next_run(schedule, now or self.now)
        return next_run - (now or self.now).replace(second=0)

    def test_inactive_schedule(self):
        self.assertEqual(
            None, get_next_run({"is_active": False, "day_of_week": self.weekdays, "create_at": "09:15:00"})
        )

    def test_next_run_same_day_later(self):
        delta = self.get_delta("09:08:00", self.weekdays)
        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 179)

    def test_next_run_same_day_later_cron_list(self):
        cron_list = ["30 07 * * *", "08 09 * * *"]
        delta = self.get_delta("09:08:00", self.weekdays, cron_list=cron_list)
        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 179)

    def test_next_run_next_day(self):
        delta = self.get_delta("09:03:00", self.weekdays)
        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 3600 * 24 - 121)

    def test_next_run_next_week(self):
        delta = self.get_delta("09:03:00", [self.now.strftime("%a").upper()])
        self.assertEqual(delta.days, 6)

    def test_next_run_now(self):
        delta = self.get_delta("09:05:00", self.weekdays)
        self.assertEqual(delta.seconds, 24 * 60 * 60 - 1)

    def test_get_item_from_template(self):
        template = {
            "_id": "foo",
            "name": "test",
            "schedule_desk": "sports",
            "schedule_stage": "schedule",
            "data": {
                "headline": "Foo",
                "dateline": {
                    "located": {"city": "Sydney", "city_code": "Sydney", "tz": "Australia/Sydney"},
                    "date": "2015-10-10T10:10:10",
                },
            },
        }
        now = utcnow()
        with self.app.app_context():
            item = get_item_from_template(template)
        self.assertNotIn("_id", item)
        self.assertEqual("foo", item.get("template"))
        self.assertEqual("Foo", item.get("headline"))
        self.assertEqual(CONTENT_STATE.SUBMITTED, item.get(ITEM_STATE))
        self.assertEqual({"desk": "sports", "stage": "schedule"}, item.get("task"))
        dateline = item.get("dateline")
        self.assertEqual("Sydney", dateline["located"]["city"])
        self.assertEqual(now, dateline.get("date"))
        self.assertIn("SYDNEY", dateline.get("text"))

    def test_next_run_for_timezone(self):
        # UTC time Zero hours
        now = datetime(2018, 6, 30, 19, 0, 0, 0, tzinfo=pytz.utc)
        current_now = now + timedelta(seconds=5)
        # schedule at 06:00 AM
        delta = self.get_delta("06:00:00", self.weekdays, time_zone="Australia/Sydney", now=current_now)
        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 3600)

        # 30 minutes before schedule
        current_now = now + timedelta(minutes=30)
        delta = self.get_delta("06:00:00", self.weekdays, time_zone="Australia/Sydney", now=current_now)
        self.assertEqual(delta.days, 0)
        self.assertEqual(delta.seconds, 1800)

        # hour after schedule
        current_now = now + timedelta(hours=1, seconds=5)
        delta = self.get_delta("06:00:00", self.weekdays, time_zone="Australia/Sydney", now=current_now)
        self.assertEqual(delta.days, 1)


class RenderTemplateTestCase(TestCase):
    def test_render_content_template(self):
        template = {
            "_id": "foo",
            "template_name": "test",
            "template_desks": ["sports"],
            "data": {
                "headline": "Foo Template: {{item.headline}}",
                "body_html": 'This article has slugline: {{item.slugline}} and dateline: {{item.dateline["text"]}} '
                'at {{item.versioncreated | format_datetime("Australia/Sydney", "%d %b %Y %H:%S %Z")}}',
                "urgency": 1,
                "priority": 3,
                "dateline": {},
                "anpa_take_key": "this is test",
                "place": ["Australia"],
            },
        }

        item = {
            "_id": "123",
            "headline": "Test Template",
            "slugline": "Testing",
            "body_html": "This is test story",
            "dateline": {"text": "hello world"},
            "urgency": 4,
            "priority": 6,
            "versioncreated": "2015-06-01T22:54:53+0000",
            "place": ["NSW"],
        }

        updates = render_content_template(item, template)
        self.assertEqual(updates["headline"], "Foo Template: Test Template")
        self.assertEqual(updates["urgency"], 1)
        self.assertEqual(updates["priority"], 3)
        self.assertEqual(
            updates["body_html"],
            "This article has slugline: Testing and dateline: " "hello world at 02 Jun 2015 08:53 AEST",
        )
        self.assertListEqual(updates["place"], ["Australia"])

    def test_headline_strip_tags(self):
        template = {"data": {"headline": " test\nit<br>"}}

        updates = render_content_template({}, template)
        self.assertEqual("test it", updates["headline"])

        item = get_item_from_template(template)
        self.assertEqual("test it", item["headline"])
