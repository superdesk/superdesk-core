# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 to present Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import unittest

from superdesk.tests import TestCase

from apps.content_lists.article_content import (
    attach_article_content,
    _build_article_content,
    _get_thumbnail,
    _first_body_html_image,
)


class BuildArticleContentTestCase(unittest.TestCase):
    """Pure unit tests for the article summary builders (no app needed)."""

    def test_headline_maps_to_title(self):
        content = _build_article_content({"headline": "Breaking news", "state": "published"})
        self.assertEqual(content["title"], "Breaking news")
        self.assertEqual(content["state"], "published")

    def test_omitted_optional_fields_absent(self):
        content = _build_article_content({"headline": "Only headline"})
        self.assertEqual(content, {"title": "Only headline"})

    def test_passthrough_fields_copied(self):
        article = {
            "anpa_category": [{"qcode": "a"}],
            "subject": [{"qcode": "01000000"}],
            "firstpublished": "2026-01-01T00:00:00+0000",
        }
        content = _build_article_content(article)
        self.assertEqual(content["anpa_category"], [{"qcode": "a"}])
        self.assertEqual(content["subject"], [{"qcode": "01000000"}])
        self.assertEqual(content["firstpublished"], "2026-01-01T00:00:00+0000")

    def test_thumbnail_prefers_featuremedia_rendition_over_body_img(self):
        article = {
            "associations": {"featuremedia": {"renditions": {"thumbnail": {"href": "https://cdn/thumb.jpg"}}}},
            "body_html": '<p><img src="https://cdn/body.jpg"></p>',
        }
        self.assertEqual(_get_thumbnail(article), {"href": "https://cdn/thumb.jpg"})

    def test_thumbnail_falls_back_to_first_body_img_src(self):
        article = {"body_html": '<p>text</p><img src="https://cdn/first.jpg"><img src="https://cdn/second.jpg">'}
        self.assertEqual(_get_thumbnail(article), "https://cdn/first.jpg")

    def test_no_thumbnail_when_nothing_available(self):
        self.assertIsNone(_get_thumbnail({"body_html": "<p>no image here</p>"}))
        self.assertIsNone(_get_thumbnail({}))

    def test_no_thumbnail_key_when_none(self):
        content = _build_article_content({"headline": "x", "body_html": "<p>plain</p>"})
        self.assertNotIn("thumbnail", content)

    def test_img_without_src_returns_none(self):
        self.assertIsNone(_first_body_html_image("<p><img alt='no source'></p>"))

    def test_empty_src_returns_none(self):
        self.assertIsNone(_first_body_html_image('<p><img src=""></p>'))

    def test_malformed_html_returns_none(self):
        self.assertIsNone(_first_body_html_image("<broken <<html"))


class AttachArticleContentTestCase(TestCase):
    """Integration tests for the archive lookup and in-place enrichment."""

    async def _seed_archive(self, docs):
        collection = self.async_app.mongo.get_collection_async("archive")
        await collection.insert_many(docs)

    async def test_empty_items_list(self):
        items = []
        await attach_article_content(items)
        self.assertEqual(items, [])

    async def test_items_with_falsy_content_get_none(self):
        items = [{"content": None}, {"content": ""}, {}]
        await attach_article_content(items)
        for item in items:
            self.assertIsNone(item["article_content"])

    async def test_missing_archive_docs_get_none(self):
        items = [{"content": "does-not-exist"}]
        await attach_article_content(items)
        self.assertIsNone(items[0]["article_content"])

    async def test_found_docs_get_summary(self):
        await self._seed_archive(
            [
                {
                    "_id": "article-1",
                    "guid": "article-1",
                    "type": "text",
                    "headline": "Hello",
                    "state": "published",
                    "body_html": '<p><img src="https://cdn/pic.jpg"></p>',
                }
            ]
        )
        items = [{"content": "article-1"}, {"content": "missing"}]
        await attach_article_content(items)

        summary = items[0]["article_content"]
        self.assertEqual(summary["title"], "Hello")
        self.assertEqual(summary["state"], "published")
        self.assertEqual(summary["thumbnail"], "https://cdn/pic.jpg")
        self.assertIsNone(items[1]["article_content"])
