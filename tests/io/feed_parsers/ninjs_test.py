# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
from superdesk.tests import TestCase
from superdesk.io.feed_parsers.ninjs import NINJSFeedParser


class NINJSTestCase(TestCase):
    vocab = [
        {"_id": "genre", "items": [{"name": "Current"}]},
        {
            "_id": "categories",
            "items": [
                {
                    "name": "Advisory",
                    "qcode": "m",
                    "translations": {"name": {"en": "Advisory", "fr": "Avis"}},
                },
            ],
        },
    ]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.data.insert("vocabularies", self.vocab)
        dirname = os.path.dirname(os.path.realpath(__file__))
        fixture = os.path.normpath(os.path.join(dirname, "../fixtures", self.filename))
        provider = {"name": "Test"}
        self.items = await NINJSFeedParser().parse(fixture, provider)


class SimpleTestCase(NINJSTestCase):
    filename = "ninjs1.json"

    def test_headline(self):
        self.assertEqual(self.items[0].get("headline"), "headline")
        self.assertEqual(self.items[0].get("description_text"), "abstract")
        self.assertEqual(1, len(self.items[0].get("authors")), "authors")
        self.assertEqual(
            self.items[0]["authors"][0],
            {
                "name": "John",
                "role": "writer",
                "avatar_url": "http://example.com",
                "biography": "bio",
            },
        )
        self.assertNotIn("source", self.items[0])
        self.assertEqual(self.items[0]["original_source"], "AAP")
        self.assertEqual("2017-08-24T04:38:34+00:00", self.items[0]["versioncreated"].isoformat())

    def test_translated_value(self):
        self.assertEqual(self.items[0].get("headline"), "headline")
        self.assertEqual(
            self.items[0].get("anpa_category"),
            [{"name": "Advisory", "qcode": "m", "translations": {"name": {"en": "Advisory", "fr": "Avis"}}}],
        )

    def test_body_html_removes_class_and_style_attributes(self):
        parser = NINJSFeedParser()
        item = parser._transform_from_ninjs(
            {
                "guid": "body-cleanup-test",
                "type": "text",
                "body_html": (
                    '<table cellspacing="0" class="bwtablemarginb bwblockalignl">'
                    '<tr><td class="bwalignr" rowspan="1" colspan="1">'
                    '<p class="bwcellpmargin" style="width:0;height:0">(1)</p>'
                    "</td></tr></table>"
                ),
            }
        )

        self.assertEqual(
            '<table cellspacing="0"><tr><td rowspan="1" colspan="1"><p>(1)</p></td></tr></table>',
            item["body_html"],
        )

    def test_body_html_attributes_to_remove_can_be_overridden(self):
        class KeepStyleNINJSFeedParser(NINJSFeedParser):
            HTML_ATTRIBUTES_TO_REMOVE = ("class",)

        item = KeepStyleNINJSFeedParser()._transform_from_ninjs(
            {
                "guid": "body-cleanup-override-test",
                "type": "text",
                "body_html": '<p class="foo" style="width:0">x</p>',
            }
        )

        self.assertEqual('<p style="width:0">x</p>', item["body_html"])

    def test_body_html_tags_to_remove_and_kill_can_be_overridden(self):
        class CustomNINJSFeedParser(NINJSFeedParser):
            HTML_TAGS_TO_REMOVE = ("span",)
            HTML_TAGS_TO_KILL = ("script", "style", "head", "aside")

        item = CustomNINJSFeedParser()._transform_from_ninjs(
            {
                "guid": "body-cleanup-tags-test",
                "type": "text",
                "body_html": "<div><span>keep text</span><aside>remove text</aside></div>",
            }
        )

        self.assertEqual("<div>keep text</div>", item["body_html"])

    def test_body_html_sanitizer_can_be_overridden(self):
        class CustomNINJSFeedParser(NINJSFeedParser):
            def _sanitize_html(self, value):
                return "custom: " + value

        item = CustomNINJSFeedParser()._transform_from_ninjs(
            {"guid": "body-cleanup-method-test", "type": "text", "body_html": "<p>text</p>"}
        )

        self.assertEqual("custom: <p>text</p>", item["body_html"])

    def test_nested_association_body_html_is_sanitized(self):
        parser = NINJSFeedParser()
        item = parser._transform_from_ninjs(
            {
                "guid": "parent",
                "type": "text",
                "associations": {
                    "child": {
                        "guid": "child",
                        "type": "text",
                        "body_html": '<p class="child">child<script>bad</script></p>',
                        "associations": {
                            "grandchild": {
                                "guid": "grandchild",
                                "type": "text",
                                "body_html": '<p style="display:none">grandchild</p>',
                            }
                        },
                    }
                },
            }
        )

        child = item["associations"]["child"]
        self.assertEqual("<p>child</p>", child["body_html"])
        self.assertEqual("<p>grandchild</p>", child["associations"]["grandchild"]["body_html"])
        self.assertEqual("<p>grandchild</p>", parser.items[0]["body_html"])
        self.assertEqual("<p>child</p>", parser.items[1]["body_html"])


class AssociatedTestCase(NINJSTestCase):
    filename = "ninjs2.json"

    def test_parsed_items(self):
        # The picture
        self.assertEqual(self.items[0].get("type"), "picture")
        self.assertEqual(self.items[0].get("headline"), "Financial Markets")
        self.assertEqual(self.items[0].get("alt_text"), "Oil markets something")
        self.assertEqual(
            self.items[0].get("description_text"),
            "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
        )
        # The text item
        self.assertEqual(self.items[1].get("type"), "text")
        self.assertEqual(self.items[1].get("headline"), "Oil prices edge up on first drop in US drilling in months")
        self.assertEqual(
            self.items[1].get("abstract"),
            "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
        )
        # The associated picture in the text item
        self.assertEqual(self.items[1].get("associations").get("featuremedia").get("type"), "picture")
        self.assertEqual(self.items[1].get("associations").get("featuremedia").get("alt_text"), "Oil markets something")
        self.assertEqual(
            self.items[1].get("associations").get("featuremedia").get("description_text"),
            "Oil prices edged up on Monday, supported by the first fall in US drilling activity in month.",
        )


class PictureTestCase(NINJSTestCase):
    filename = "ninjs3.json"

    def test_headline(self):
        self.assertEqual(self.items[0].get("headline"), "German Air Force Museum")
        self.assertEqual(self.items[0].get("type"), "picture")


class IPTCSimpleTextTestCase(NINJSTestCase):
    filename = "ninjsExSimpleText1.json"

    def test_simple(self):
        self.assertEqual(1, len(self.items))
        item = self.items[0]
        self.assertEqual("urn:ninjs.example.com:newsitems:20130709simp123", item["guid"])
        self.assertEqual("2013-07-09T10:37:00+00:00", item["versioncreated"].isoformat())
        self.assertIn("GROSSETO", item["body_html"])


class IPTCMediumTextTestCase(NINJSTestCase):
    filename = "ninjsExMediumText1.json"

    def test_medium(self):
        self.assertEqual(1, len(self.items))
        self.assertEqual("text-only", self.items[0]["profile"])
        self.assertEqual("en", self.items[0]["language"])


class EmbargoedTestCase(NINJSTestCase):
    filename = "ninjs_embargoed.json"

    def test_embargo(self):
        self.assertEqual(2, len(self.items))
        self.assertEqual("2022-06-29T02:30:00+00:00", self.items[1]["embargoed"].isoformat())
