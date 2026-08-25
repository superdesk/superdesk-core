# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Utilities for extractid metadata from image files."""

import io
import logging

from typing import BinaryIO, Dict, List, Union

from superdesk.text_utils import decode
from PIL import Image, ExifTags, ImageOps
from PIL import IptcImagePlugin
from PIL.TiffImagePlugin import IFDRational

from superdesk.core import json
from superdesk.media.metadata_mapping import MediaMetadata
from .iim_codes import iim_codes

logger = logging.getLogger(__name__)

try:
    import pyexiv2
except ImportError:
    logging.warning("pyexiv2 is not installed, writing picture metadata will not work")
    pass


ORIENTATIONS = {
    1: ("Normal", 0),
    2: ("Mirrored left-to-right", 0),
    3: ("Rotated 180 degrees", 180),
    4: ("Mirrored top-to-bottom", 0),
    5: ("Mirrored along top-left diagonal", 0),
    6: ("Rotated 90 degrees", -90),
    7: ("Mirrored along top-right diagonal", 0),
    8: ("Rotated 270 degrees", -270),
}
EXIF_ORIENTATION_TAG = 274


def fix_orientation(file_stream):
    """Returns the image fixed accordingly to the orientation.

    @param file_stream: stream
    """
    file_stream.seek(0)
    img = Image.open(file_stream)
    file_stream.seek(0)

    getexif = getattr(img, "getexif", None)
    if not getexif:
        return file_stream

    exif = getexif()
    if not exif or exif.get(EXIF_ORIENTATION_TAG) == 1:
        return file_stream

    normalized = ImageOps.exif_transpose(img)
    exif = normalized.getexif()
    exif[EXIF_ORIENTATION_TAG] = 1

    image_format = img.format or "JPEG"
    if image_format == "JPEG" and normalized.mode not in ("RGB", "L"):
        normalized = normalized.convert("RGB")

    output = io.BytesIO()
    normalized.save(output, image_format, exif=exif.tobytes())
    output.seek(0)
    setattr(output, "width", normalized.size[0])
    setattr(output, "height", normalized.size[1])
    return output


def get_meta(file_stream):
    """Returns the image metadata in a dictionary of tag:value pairs.

    @param file_stream: stream
    """
    current = file_stream.tell()
    file_stream.seek(0)
    img = Image.open(file_stream)
    try:
        rv = img.getexif()
    except AttributeError:
        return {}
    if not rv:
        return {}
    exif = dict(rv)
    file_stream.seek(current)

    exif_meta = {}
    for k, v in exif.items():
        logger.debug("Attempting exif key %s, val %s", k, v)
        try:
            key = ExifTags.TAGS[k].strip()
        except KeyError:
            logger.debug("\tKey not found")
            continue

        logger.debug("\tUpdated key = %s", key)

        if key == "GPSInfo":
            logger.debug("\tKey is for GPS Info")
            # lookup GPSInfo description key names
            value = {
                ExifTags.GPSTAGS[vk].strip(): convert_exif_value(vv, vk)
                for vk, vv in rv.get_ifd(k).items()
                if is_serializable(vv)
            }
            logger.debug(value)
            exif_meta[key] = value
        elif is_serializable(v):
            value = v.decode("UTF-8") if isinstance(v, bytes) else v
            exif_meta[key] = convert_exif_value(value)

    # Remove this as it's too long to send in headers
    exif_meta.pop("UserComment", None)

    return exif_meta


def convert_exif_value(val, key=None):
    if ExifTags.GPSTAGS.get(key) == "GPSAltitudeRef":
        return 0 if val == b"\x00" else 1
    if isinstance(val, tuple):
        return tuple([convert_exif_value(v) for v in val])
    if isinstance(val, list):
        return list([convert_exif_value(v) for v in val])
    if isinstance(val, IFDRational):
        try:
            return float(str(val._val))
        except ValueError:
            numerator, denominator = val.limit_rational(100)
            return round(numerator / denominator, 3)
    return val


def is_serializable(val):
    try:
        json.dumps(convert_exif_value(val))
    except (TypeError, ValueError):
        return False
    return True


def get_meta_iptc(file_stream: BinaryIO):
    """Returns the image IPTC metadata in a dictionary of tag:value pairs.

    @param file_stream: stream
    """
    file_stream.seek(0)
    img = Image.open(file_stream)
    iptc_raw = IptcImagePlugin.getiptcinfo(img)
    metadata: Dict[str, Union[str, List[str]]] = {}

    if iptc_raw is None:
        return metadata

    for code, value in iptc_raw.items():
        try:
            tag = iim_codes[code]
        except KeyError:
            continue
        if isinstance(value, list):
            metadata[tag] = [decode(v) for v in value]
        elif isinstance(value, bytes):
            metadata[tag] = decode(value)
    return metadata


def read_metadata(input: bytes) -> MediaMetadata:
    """Reads the metadata from the image file.

    @param file_stream: stream
    """
    try:
        with pyexiv2.ImageData(input) as img:
            xmp = img.read_xmp()
    except (RuntimeError, ValueError) as e:
        logger.warning("Failed to read image metadata with pyexiv2: %s, trying exiftool fallback", e, exc_info=True)
        # Try to use exiftool as fallback when pyexiv2 fails
        # Import here to avoid loading exiftool dependencies unless needed (lazy loading)
        from superdesk.media.video import read_metadata as read_metadata_video

        # Map video module metadata to image module field names
        return _map_video_to_image(read_metadata_video(input))

    return {
        "Description": get_xmp_lang_string(xmp.get("Xmp.dc.description")),
        "DescriptionWriter": xmp.get("Xmp.photoshop.CaptionWriter", ""),
        "Headline": xmp.get("Xmp.photoshop.Headline", ""),
        "Instructions": xmp.get("Xmp.photoshop.Instructions", ""),
        "JobId": xmp.get("Xmp.photoshop.TransmissionReference", ""),
        "Title": get_xmp_lang_string(xmp.get("Xmp.dc.title")),
        "Creator": xmp.get("Xmp.dc.creator", []),
        "CreatorsJobtitle": xmp.get("Xmp.photoshop.AuthorsPosition", ""),
        "CopyrightNotice": get_xmp_lang_string(xmp.get("Xmp.dc.rights", "")),
        "City": xmp.get("Xmp.photoshop.City", ""),
        "Country": xmp.get("Xmp.photoshop.Country", ""),
        "CountryCode": xmp.get("Xmp.iptc.CountryCode", ""),
        "CreditLine": xmp.get("Xmp.photoshop.Credit", ""),
        "ProvinceState": xmp.get("Xmp.photoshop.State", ""),
    }


# Field mappings between image module and video module field names
# Keys are video module names, values are image module names
_FIELD_MAPPING: Dict[str, str] = {
    "CaptionWriter": "DescriptionWriter",
    "TransmissionReference": "JobId",
    "AuthorsPosition": "CreatorsJobtitle",
    "Rights": "CopyrightNotice",
    "State": "ProvinceState",
    "Credit": "CreditLine",
}


def _map_video_to_image(metadata: MediaMetadata) -> MediaMetadata:
    """Map video module metadata field names to image module field names.

    Converts video module field names to image module field names for consistency.

    @param metadata: Metadata dict from exiftool fallback
    @return: Metadata with image module field names
    """
    result: MediaMetadata = {}

    for key, value in metadata.items():
        # Use mapped name if available, otherwise keep original name
        mapped_key = _FIELD_MAPPING.get(key, key)
        result[mapped_key] = value  # type: ignore[literal-required]

    return result


def _map_image_to_video(metadata: MediaMetadata) -> MediaMetadata:
    """Map image module metadata field names to video module field names.

    Converts image module field names back to video module field names for
    compatibility with the video module's exiftool handler.

    @param metadata: Metadata dict with image module field names
    @return: Metadata with video module field names
    """
    # Create reverse mapping: image module field names to video module field names
    reverse_mapping = {v: k for k, v in _FIELD_MAPPING.items()}

    result: MediaMetadata = {}
    for key, value in metadata.items():
        # Use reverse mapped name if available, otherwise keep original name
        mapped_key = reverse_mapping.get(key, key)
        result[mapped_key] = value  # type: ignore[literal-required]

    return result


def get_xmp_lang_string(value, lang="x-default"):
    lang_key = 'lang="{}"'.format(lang)
    if value and isinstance(value, dict) and value.get(lang_key):
        return value[lang_key]
    if value and isinstance(value, str):
        return value
    return ""


def write_metadata(input: bytes, metadata: MediaMetadata) -> bytes:
    """Writes the metadata to the image file.

    @param file_stream: stream
    @param metadata: dict
    """
    from pyexiv2 import convert_xmp_to_iptc

    xmp = {
        "Xmp.dc.description": metadata.get("Description"),
        "Xmp.photoshop.CaptionWriter": metadata.get("DescriptionWriter"),
        "Xmp.photoshop.Headline": metadata.get("Headline"),
        "Xmp.photoshop.Instructions": metadata.get("Instructions"),
        "Xmp.photoshop.TransmissionReference": metadata.get("JobId"),
        "Xmp.dc.title": metadata.get("Title"),
        "Xmp.dc.creator": metadata.get("Creator"),
        "Xmp.photoshop.AuthorsPosition": metadata.get("CreatorsJobtitle"),
        "Xmp.dc.rights": metadata.get("CopyrightNotice"),
        "Xmp.photoshop.City": metadata.get("City"),
        "Xmp.photoshop.Country": metadata.get("Country"),
        "Xmp.iptc.CountryCode": metadata.get("CountryCode"),
        "Xmp.photoshop.Credit": metadata.get("CreditLine"),
        "Xmp.photoshop.State": metadata.get("ProvinceState"),
    }

    xmp = {k: v for k, v in xmp.items() if v}
    iptc = convert_xmp_to_iptc(xmp)

    try:
        with pyexiv2.ImageData(input) as img:
            img.modify_xmp(xmp)
            img.modify_iptc(iptc)
            return img.get_bytes()
    except (RuntimeError, ValueError) as e:
        logger.warning("Failed to write image metadata with pyexiv2: %s, trying exiftool fallback", e, exc_info=True)
        # Try to use exiftool as fallback when pyexiv2 fails
        # Import here to avoid loading exiftool dependencies unless needed (lazy loading)
        from superdesk.media.video import write_metadata as write_metadata_video

        # Map image module metadata to video module field names
        mapped_metadata = _map_image_to_video(metadata)
        return write_metadata_video(input, mapped_metadata)
