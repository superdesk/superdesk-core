# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
import unittest

from unittest.mock import patch
from datetime import datetime, timedelta

from apps.templates.filters import format_datetime_filter
from apps.templates.content_templates import get_item_from_template, render_content_template


class RenderTemplateTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.app_context().push()
        self.app.jinja_env.filters["format_datetime"] = format_datetime_filter

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

    def test_render_dateline_current_time(self):
        now = datetime(2020, 12, 8, 13, 0, 0)
        template = {
            "data": {
                "dateline": {
                    "located": {
                        "dateline": "city",
                        "tz": "Europe/Prague",
                        "city": "Prague",
                        "city_code": "Prague",
                        "country_code": "CZ",
                        "state_code": "52",
                    },
                    "date": now - timedelta(days=5),
                    "text": "PRAGUE, Dec 3 -",
                },
            }
        }

        with patch("apps.templates.content_templates.utcnow", return_value=now):
            updates = render_content_template({}, template)
        self.assertEqual("PRAGUE, Dec 8  -", updates["dateline"]["text"])
