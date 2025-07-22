# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any, TypedDict
from hachoir.stream import InputIOStream
from hachoir.parser import guessParser
from hachoir.metadata import extractMetadata
from flask import json
import logging
from superdesk.media.image import PhotoMetadata


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


class VideoMetadata(TypedDict, total=False):
    Description: str | None
    CaptionWriter: str | None
    Headline: str | None
    Instructions: str | None
    TransmissionReference: str | None
    Title: str | None
    Creator: list[str] | str | None
    AuthorsPosition: str | None
    Rights: str | None
    City: str | None
    Country: str | None
    CountryCode: str | None
    Credit: str | None
    State: str | None
    Location: str | None
    CreatorContactInfo: str | None
    Language: str | None
    Destination: str | None
    ServiceIdentifier: str | None
    ProductID: str | None
    DateSent: str | None
    TimeSent: str | None
    EditStatus: str | None
    Urgency: str | None
    SubjectCode: str | None
    Category: str | None
    SupplementalCategories: str | None
    Subject: str | None
    LocationCode: str | None
    LocationName: str | None
    ReleaseDate: str | None
    ReleaseTime: str | None
    ExpirationDate: str | None
    ExpirationTime: str | None
    TimeCreated: str | None
    Source: str | None
    DateCreated: str | None


VideoMetadataKeys = set(VideoMetadata.__annotations__.keys())


def read_with_exiftool(bin: bytes) -> dict[str, Any]:
    import tempfile
    from exiftool import ExifToolHelper  # type: ignore
    from exiftool.exceptions import ExifToolException  # type: ignore

    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(bin)
        tmp.flush()

        try:
            with ExifToolHelper() as et:
                return et.get_metadata(tmp.name, ["-xmp:all"])[0]
        except ExifToolException as e:
            logger.exception(e.stderr)
            return {}


def read_metadata(bin: bytes) -> VideoMetadata:
    from typing import cast

    raw_metadata = read_with_exiftool(bin)
    metadata = {kk: v for k, v in raw_metadata.items() if v and (kk := k.replace("XMP:", "")) in VideoMetadataKeys}
    return cast(VideoMetadata, metadata)


def write_metadata(bin: bytes, video: VideoMetadata) -> bytes:
    return write_with_exiftool(bin, map_exiftool_args(video))


def get_video_from_photo(photo: PhotoMetadata) -> VideoMetadata:
    """Get XMP from IPTC and truthy custom tags

    @param metadata: PhotoMetadata
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
    return cast(VideoMetadata, tags)


def map_exiftool_args(video: VideoMetadata) -> list[str]:
    args = ["-sep", ","]
    args.extend(f"-{k}={','.join(v) if isinstance(v, list) else v}" for k, v in video.items())
    args.append("-overwrite_original")
    return args


def write_with_exiftool(bin: bytes, args: list[str]) -> bytes:
    import tempfile
    from exiftool import ExifToolHelper
    from exiftool.exceptions import ExifToolExecuteError
    from os import remove

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(bin)
        tmp.flush()
        path = tmp.name

    try:
        with ExifToolHelper() as et:
            et.execute(*args, path)

        with open(path, "rb") as r:
            return r.read()
    except ExifToolExecuteError as e:
        logger.exception(e.stderr)
        return bin
    finally:
        remove(path)
