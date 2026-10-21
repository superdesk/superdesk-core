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
from superdesk.media.metadata_mapping import MediaMetadataKeys
from superdesk.media.video_editor import VideoEditorWrapper
from superdesk.metadata.item import CONTENT_TYPE_LITERAL
from .upload_staging_types import MetadataStatus, StagedMetadata, StagedUpload

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

# XMP fallbacks for the ExifTool IPTC names used by client iptcMapping extensions.
IPTC_XMP_TAGS = {
    "Destination": "Destination",
    "ServiceIdentifier": "ServiceIdentifier",
    "ProductID": "ProductID",
    "DateSent": "DateSent",
    "TimeSent": "TimeSent",
    "ObjectName": "Title",
    "EditStatus": "EditStatus",
    "Urgency": "Urgency",
    "SubjectReference": "SubjectCode",
    "Category": "Category",
    "SupplementalCategories": "SupplementalCategories",
    "Keywords": "Subject",
    "ContentLocationCode": "LocationCode",
    "ContentLocationName": "LocationName",
    "ReleaseDate": "ReleaseDate",
    "ReleaseTime": "ReleaseTime",
    "ExpirationDate": "ExpirationDate",
    "ExpirationTime": "ExpirationTime",
    "SpecialInstructions": "Instructions",
    "DateCreated": "DateCreated",
    "TimeCreated": "TimeCreated",
    "By-line": "Creator",
    "By-lineTitle": "AuthorsPosition",
    "City": "City",
    "Sub-location": "Location",
    "Province-State": "State",
    "Country-PrimaryLocationCode": "CountryCode",
    "Country-PrimaryLocationName": "Country",
    "OriginalTransmissionReference": "TransmissionReference",
    "Headline": "Headline",
    "Credit": "Credit",
    "Source": "Source",
    "CopyrightNotice": "Rights",
    "Contact": "CreatorContactInfo",
    "Caption-Abstract": "Description",
    "Writer-Editor": "CaptionWriter",
    "LanguageIdentifier": "Language",
}


PICTURE_XMP_TAGS = {
    "Description": "Description",
    "DescriptionWriter": "CaptionWriter",
    "Headline": "Headline",
    "Instructions": "Instructions",
    "JobId": "TransmissionReference",
    "Title": "Title",
    "Creator": "Creator",
    "CreatorsJobtitle": "AuthorsPosition",
    "CopyrightNotice": "Rights",
    "City": "City",
    "Country": "Country",
    "CountryCode": "CountryCode",
    "CreditLine": "Credit",
    "ProvinceState": "State",
}


def read_staged_metadata(path: str, content_type: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract once and derive canonical and hook metadata from the same tags."""
    from exiftool import ExifToolHelper

    with ExifToolHelper() as tool:
        raw = tool.get_metadata(path, ["-G", "-xmp:all", "-iptc:all"])[0]
    if content_type == "image":
        canonical = {field: raw.get(f"XMP:{tag}", "") for field, tag in PICTURE_XMP_TAGS.items()}
        creator = canonical["Creator"]
        canonical["Creator"] = creator if isinstance(creator, list) else [creator] if creator else []
    else:
        canonical = {
            key.removeprefix("XMP:"): value
            for key, value in raw.items()
            if key.startswith("XMP:") and key.removeprefix("XMP:") in MediaMetadataKeys and value
        }

    metadata = {}
    for iptc, xmp in IPTC_XMP_TAGS.items():
        value = raw.get(f"XMP:{xmp}")
        if content_type == "image":
            iptc_value = raw.get(f"IPTC:{iptc}")
            if iptc_value not in (None, ""):
                value = iptc_value
        if isinstance(value, str):
            value = value.strip()
        if value not in (None, ""):
            metadata[iptc] = value

    # XMP stores creation date and time together; CP also expects TimeCreated.
    created = metadata.get("DateCreated")
    if isinstance(created, str) and not metadata.get("TimeCreated"):
        date_time = created.replace("T", " ", 1).split(" ", 1)
        if len(date_time) == 2:
            metadata["TimeCreated"] = date_time[1]
    return canonical, metadata


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


async def delete_staged_media(staged: StagedUpload, *, original: bool = True) -> None:
    media_ids = {rend["media"] for rend in staged.get("renditions", {}).values() if rend.get("media")}
    if original:
        media_ids.add(staged["media"])
    else:
        media_ids.discard(staged["media"])
    media = get_current_app().media
    deletions = [media.delete_async(media_id) for media_id in media_ids]
    await asyncio.gather(*deletions)
    if staged.get("video_server_id"):
        VideoEditorWrapper()._delete(staged["video_server_id"])


async def extract_staged_metadata(staged: StagedUpload, content: IO[bytes], path: str) -> StagedMetadata:
    file_type = staged["mimetype"].split("/")[0]
    updates: StagedMetadata = {"metadata_status": MetadataStatus.READY}

    def parse() -> StagedMetadata:
        try:
            raw, iptc = ({}, {}) if file_type == "audio" else read_staged_metadata(path, file_type)
            mapping_input = raw.copy()
            if file_type == "video":
                for canonical, alias in (("CopyrightNotice", "Rights"), ("CreditLine", "Credit")):
                    if alias in raw:
                        mapping_input.setdefault(canonical, raw[alias])
            return {
                "raw_metadata": raw,
                "iptc_metadata": iptc,
                "meta": map_metadata_to_article(mapping_input, staged.get("meta")),
            }
        except Exception:
            logger.exception("Failed to extract embedded metadata for %s", staged["_id"])
            return {
                "metadata_status": MetadataStatus.FAILED,
                "metadata_error": str(_("Metadata extraction failed. Enter metadata manually.")),
            }

    updates.update(await asyncio.to_thread(parse))
    content.seek(0)
    metadata = await asyncio.to_thread(process_file, content, file_type)
    metadata["length"] = staged["size"]
    set_filemeta(updates, decode_metadata(encode_metadata(metadata)))
    return updates
