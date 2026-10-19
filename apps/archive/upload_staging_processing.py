# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Media helpers for staged uploads."""

import asyncio
import logging
from typing import Any, IO

from quart_babel import gettext as _

from superdesk.core import get_app_config, get_current_app
from superdesk.filemeta import set_filemeta
from superdesk.media.media_operations import process_file, encode_metadata, decode_metadata
from superdesk.media.metadata import read_metadata
from superdesk.media.video_editor import VideoEditorWrapper
from superdesk.metadata.item import CONTENT_TYPE_LITERAL

logger = logging.getLogger(__name__)

STAGEABLE_FILE_TYPES: dict[str, CONTENT_TYPE_LITERAL] = {
    "image": "picture",
    "audio": "audio",
    "video": "video",
}

#: article field -> embedded metadata key, can be extended using ``PICTURE_METADATA_MAPPING``
DEFAULT_METADATA_MAPPING = {
    "byline": "Creator",
    "headline": "Headline",
    "description_text": "Description",
    "copyrightnotice": "CopyrightNotice",
    "creditline": "CreditLine",
}


def map_metadata_to_article(raw_metadata: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map embedded media metadata to article fields."""
    mapping = {**DEFAULT_METADATA_MAPPING, **(get_app_config("PICTURE_METADATA_MAPPING") or {})}
    meta: dict[str, Any] = {}

    for field, key in mapping.items():
        value = raw_metadata.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v)
        if value in (None, ""):
            continue
        if field.startswith("extra."):
            meta.setdefault("extra", {})[field[len("extra.") :]] = value
        else:
            meta[field] = value

    if not meta.get("byline") and user and user.get("byline"):
        meta["byline"] = user["byline"]

    return meta


async def delete_staged_media(staged: dict, *, original: bool = True) -> None:
    media_ids = {rend["media"] for rend in staged.get("renditions", {}).values() if rend.get("media")}
    if original:
        media_ids.add(staged["media"])
    else:
        media_ids.discard(staged["media"])
    for media_id in media_ids:
        await get_current_app().media.delete_async(media_id)
    if staged.get("video_server_id"):
        VideoEditorWrapper()._delete(staged["video_server_id"])


async def extract_staged_metadata(staged: dict, content: IO[bytes], path: str) -> dict:
    file_type = staged["mimetype"].split("/")[0]
    updates = {"metadata_status": "ready"}

    def parse():
        try:
            raw = {} if file_type == "audio" else dict(read_metadata(path, STAGEABLE_FILE_TYPES[file_type]))
            mapping_input = raw.copy()
            if file_type == "video":
                for canonical, alias in (("CopyrightNotice", "Rights"), ("CreditLine", "Credit")):
                    if alias in raw:
                        mapping_input.setdefault(canonical, raw[alias])
            return {"raw_metadata": raw, "meta": map_metadata_to_article(mapping_input, staged.get("meta"))}
        except Exception:
            logger.exception("Failed to extract embedded metadata for %s", staged["_id"])
            return {
                "metadata_status": "failed",
                "metadata_error": str(_("Metadata extraction failed. Enter metadata manually.")),
            }

    updates.update(await asyncio.to_thread(parse))
    content.seek(0)
    metadata = await asyncio.to_thread(process_file, content, file_type)
    metadata["length"] = staged["size"]
    set_filemeta(updates, decode_metadata(encode_metadata(metadata)))
    return updates
