# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any
from hachoir.stream import InputIOStream
from hachoir.parser import guessParser
from hachoir.metadata import extractMetadata
from flask import json
import logging
from superdesk.media.metadata_mapping import MediaMetadata, MediaMetadataKeys


logger = logging.getLogger(__name__)


def get_meta(filestream):
    metadata = {}

    try:
        filestream.seek(0)
        stream = InputIOStream(filestream, None, tags=[])
        parser = guessParser(stream)
        if not parser:
            return metadata

        tags = extractMetadata(parser).exportPlaintext(human=False, line_prefix="")
        for text in tags:
            try:
                json.dumps(text)
                key, value = text.split(":", maxsplit=1)
                key, value = key.strip(), value.strip()
                if key and value:
                    metadata.update({key: value})
            except Exception as ex:
                logger.exception(ex)
    except Exception as ex:
        logger.exception(ex)
        return metadata
    return metadata


def read_with_exiftool(bin: bytes) -> dict[str, Any]:
    from tempfile import NamedTemporaryFile
    from exiftool import ExifToolHelper  # type: ignore
    from exiftool.exceptions import ExifToolExecuteError  # type: ignore

    with NamedTemporaryFile(delete=True) as tmp:
        tmp.write(bin)
        tmp.flush()

        try:
            with ExifToolHelper() as et:
                return et.get_metadata(tmp.name, ["-xmp:all"])[0]
        except ExifToolExecuteError as e:
            logger.exception(e.stderr)
            return {}


def read_metadata(bin: bytes) -> MediaMetadata:
    from typing import cast

    raw_metadata = read_with_exiftool(bin)
    metadata = {kk: v for k, v in raw_metadata.items() if v and (kk := k.replace("XMP:", "")) in MediaMetadataKeys}
    return cast(MediaMetadata, metadata)


def write_metadata(bin: bytes, video: MediaMetadata) -> bytes:
    return write_with_exiftool(bin, map_exiftool_args(video))


def get_video_from_photo(photo: MediaMetadata) -> MediaMetadata:
    """Get XMP from IPTC and truthy custom tags

    @param photo: Metadata
    """

    from typing import cast

    xmp = {
        "Description": photo.get("Caption-Abstract", photo.get("Description")),
        "CaptionWriter": photo.get("Writer-Editor", photo.get("DescriptionWriter")),
        "Headline": photo.get("Headline"),
        "Instructions": photo.get("SpecialInstructions", photo.get("Instructions")),
        "TransmissionReference": photo.get("OriginalTransmissionReference", photo.get("JobId")),
        "Title": photo.get("ObjectName", photo.get("Title")),
        "Creator": photo.get("By-line", photo.get("Creator")),
        "AuthorsPosition": photo.get("By-lineTitle", photo.get("CreatorsJobtitle")),
        "Rights": photo.get("CopyrightNotice"),
        "City": photo.get("City"),
        "Country": photo.get("Country-PrimaryLocationName", photo.get("Country")),
        "CountryCode": photo.get("Country-PrimaryLocationCode", photo.get("CountryCode")),
        "Credit": photo.get("Credit", photo.get("CreditLine")),
        "State": photo.get("Province-State", photo.get("ProvinceState")),
        "Location": photo.get("Sub-location"),
        "CreatorContactInfo": photo.get("Contact"),
        "Language": photo.get("LanguageIdentifier"),
        "Destination": photo.get("Destination"),
        "ServiceIdentifier": photo.get("ServiceIdentifier"),
        "ProductID": photo.get("ProductID"),
        "DateSent": photo.get("DateSent"),
        "TimeSent": photo.get("TimeSent"),
        "EditStatus": photo.get("EditStatus"),
        "Urgency": photo.get("Urgency"),
        "SubjectCode": photo.get("SubjectReference"),
        "Category": photo.get("Category"),
        "SupplementalCategories": photo.get("SupplementalCategories"),
        "Subject": photo.get("Keywords"),
        "LocationCode": photo.get("ContentLocationCode"),
        "LocationName": photo.get("ContentLocationName"),
        "ReleaseDate": photo.get("ReleaseDate"),
        "ReleaseTime": photo.get("ReleaseTime"),
        "ExpirationDate": photo.get("ExpirationDate"),
        "ExpirationTime": photo.get("ExpirationTime"),
        "TimeCreated": photo.get("TimeCreated"),
        "Source": photo.get("Source"),
        **(
            {"DateCreated": f"{photo.get('DateCreated')}T{photo.get('TimeCreated')}"}
            if photo.get("DateCreated") and photo.get("TimeCreated")
            else {}
        ),
    }
    tags = {k: vv for k, v in xmp.items() if (vv := v or photo.get(k))}
    return cast(MediaMetadata, tags)


def map_exiftool_args(video: MediaMetadata) -> list[str]:
    args = ["-sep", ","]
    args.extend(f"-{k}={','.join(v) if isinstance(v, list) else v}" for k, v in video.items())
    args.append("-overwrite_original_in_place")
    return args


def write_with_exiftool(bin: bytes, args: list[str]) -> bytes:
    from tempfile import NamedTemporaryFile
    from exiftool import ExifToolHelper
    from exiftool.exceptions import ExifToolExecuteError

    try:
        with NamedTemporaryFile() as tmp:
            tmp.write(bin)
            tmp.flush()
            with ExifToolHelper() as et:
                et.execute(*args, tmp.name)

            tmp.seek(0)
            return tmp.read()
    except ExifToolExecuteError as e:
        logger.exception("ExifTool write failed: %s", e)
        return bin
