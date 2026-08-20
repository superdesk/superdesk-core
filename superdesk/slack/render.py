# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Block Kit rendering of entity previews for ``chat.unfurl``.

Unfurl attachments only accept a subset of Block Kit, so this sticks to ``section`` and ``context``
blocks and never emits ``rich_text``.
"""

import logging

from datetime import datetime

from superdesk.entity_preview.models import EntityPreview, PreviewLevel


logger = logging.getLogger(__name__)

#: Slack rejects a text object longer than this.
MAX_TEXT_LENGTH = 3000

MAX_TITLE_LENGTH = 200

#: Slack rejects a context block with more elements than this.
MAX_CONTEXT_ELEMENTS = 10

DATE_FORMAT = "%Y-%m-%d %H:%M UTC"

RESTRICTED_TEXT = "Details are restricted."

OPEN_LINK_TEXT = "Open in Superdesk"


def escape(text: str) -> str:
    """Escape the three characters Slack treats as markup in mrkdwn text."""

    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _mrkdwn(text: str) -> dict:
    return {"type": "mrkdwn", "text": _truncate(text, MAX_TEXT_LENGTH)}


def _section(text: str) -> dict:
    return {"type": "section", "text": _mrkdwn(text)}


def _format_updated(updated: datetime) -> str:
    return "Updated {}".format(updated.strftime(DATE_FORMAT))


def _link_block(preview: EntityPreview) -> dict:
    return _section("<{}|{}>".format(preview.url, OPEN_LINK_TEXT))


def _title(preview: EntityPreview) -> str:
    return "*{}*".format(escape(_truncate(preview.title, MAX_TITLE_LENGTH)))


def render_preview(preview: EntityPreview) -> list[dict]:
    """Block Kit blocks for one preview."""

    if preview.level == PreviewLevel.GENERIC:
        return [
            _section("{}\n{}".format(_title(preview), RESTRICTED_TEXT)),
            _link_block(preview),
        ]

    heading = _title(preview)
    subtitle = escape(preview.type_label)
    if preview.status:
        subtitle = "{} · {}".format(subtitle, escape(preview.status))

    blocks = [_section("{}\n{}".format(heading, subtitle))]

    elements = [_mrkdwn("*{}:* {}".format(escape(label), escape(value))) for label, value in preview.fields]
    if preview.updated:
        elements.append(_mrkdwn(_format_updated(preview.updated)))

    if elements:
        blocks.append({"type": "context", "elements": elements[:MAX_CONTEXT_ELEMENTS]})

    blocks.append(_link_block(preview))
    return blocks


def render_unfurls(previews: dict[str, EntityPreview]) -> dict[str, dict]:
    """Map of url -> unfurl payload, as ``chat.unfurl`` expects it."""

    return {
        url: {"blocks": render_preview(preview)}
        for url, preview in previews.items()
        if preview.level != PreviewLevel.NONE
    }
