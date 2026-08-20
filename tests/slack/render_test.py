import json
import unittest

from datetime import datetime, timezone

from superdesk.entity_preview.models import EntityPreview, EntityRef, PreviewLevel
from superdesk.slack.render import MAX_TITLE_LENGTH, escape, render_preview, render_unfurls


URL = "https://news.example.com/#/workspace?item=item1&action=view"


def preview(level: PreviewLevel = PreviewLevel.FULL, **overrides) -> EntityPreview:
    values = dict(
        ref=EntityRef(type="content", id="item1"),
        level=level,
        title="Rates <up> & down",
        type_label="Text story",
        fields=[("Desk", "Sports & <news>"), ("Stage", "Working stage")],
        status="In progress",
        updated=datetime(2026, 8, 20, 14, 5, tzinfo=timezone.utc),
        url=URL,
    )
    values.update(overrides)
    return EntityPreview(**values)  # type: ignore[arg-type]


class RenderPreviewTestCase(unittest.TestCase):
    def test_escape(self):
        self.assertEqual("a &amp; b &lt;c&gt;", escape("a & b <c>"))

    def test_full_preview_blocks(self):
        blocks = render_preview(preview())

        self.assertEqual(["section", "context", "section"], [block["type"] for block in blocks])
        self.assertEqual(
            {"type": "mrkdwn", "text": "*Rates &lt;up&gt; &amp; down*\nText story · In progress"},
            blocks[0]["text"],
        )
        self.assertEqual(
            [
                {"type": "mrkdwn", "text": "*Desk:* Sports &amp; &lt;news&gt;"},
                {"type": "mrkdwn", "text": "*Stage:* Working stage"},
                {"type": "mrkdwn", "text": "Updated 2026-08-20 14:05 UTC"},
            ],
            blocks[1]["elements"],
        )
        self.assertEqual({"type": "mrkdwn", "text": f"<{URL}|Open in Superdesk>"}, blocks[2]["text"])

    def test_no_rich_text_blocks(self):
        for level in (PreviewLevel.FULL, PreviewLevel.GENERIC):
            rendered = json.dumps(render_preview(preview(level)))
            self.assertNotIn("rich_text", rendered)

    def test_context_block_is_skipped_when_there_is_nothing_to_show(self):
        blocks = render_preview(preview(fields=[], updated=None))
        self.assertEqual(["section", "section"], [block["type"] for block in blocks])

    def test_status_is_optional(self):
        blocks = render_preview(preview(status=None))
        self.assertEqual("*Rates &lt;up&gt; &amp; down*\nText story", blocks[0]["text"]["text"])

    def test_title_is_truncated(self):
        blocks = render_preview(preview(title="a" * 500))
        title_line = blocks[0]["text"]["text"].splitlines()[0]
        self.assertEqual(MAX_TITLE_LENGTH + len("**"), len(title_line))
        self.assertTrue(title_line.startswith("*aaa"))

    def test_generic_preview_blocks(self):
        blocks = render_preview(preview(PreviewLevel.GENERIC, title="Superdesk content item", fields=[], status=None))

        self.assertEqual(["section", "section"], [block["type"] for block in blocks])
        self.assertEqual(
            {"type": "mrkdwn", "text": "*Superdesk content item*\nDetails are restricted."},
            blocks[0]["text"],
        )
        self.assertEqual({"type": "mrkdwn", "text": f"<{URL}|Open in Superdesk>"}, blocks[1]["text"])


class RenderUnfurlsTestCase(unittest.TestCase):
    def test_maps_urls_to_block_payloads(self):
        unfurls = render_unfurls({URL: preview()})
        self.assertEqual([URL], list(unfurls))
        self.assertEqual(render_preview(preview()), unfurls[URL]["blocks"])

    def test_skips_previews_with_no_level(self):
        other = "https://news.example.com/#/workspace?item=item2&action=view"
        unfurls = render_unfurls({URL: preview(), other: preview(PreviewLevel.NONE, url=other)})
        self.assertEqual([URL], list(unfurls))

    def test_empty(self):
        self.assertEqual({}, render_unfurls({}))
