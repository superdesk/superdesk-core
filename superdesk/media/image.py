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
from superdesk.text_utils import decode
from PIL import Image, ExifTags
from PIL import IptcImagePlugin
from PIL.TiffImagePlugin import IFDRational
from flask import json
from .iim_codes import iim_codes

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
    if not hasattr(img, "_getexif"):
        return file_stream
    rv = img._getexif()
    if not rv:
        return file_stream
    exif = dict(rv)
    if exif.get(EXIF_ORIENTATION_TAG, None):
        orientation = exif.get(EXIF_ORIENTATION_TAG)
        if orientation in [3, 6, 8]:
            degrees = ORIENTATIONS[orientation][1]
            img2 = img.rotate(degrees)
            output = io.BytesIO()
            img2.save(output, "jpeg")
            output.seek(0)
            return output
    return file_stream


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
        try:
            key = ExifTags.TAGS[k].strip()
        except KeyError:
            continue

        if key == "GPSInfo":
            # lookup GPSInfo description key names
            value = {
                ExifTags.GPSTAGS[vk].strip(): convert_exif_value(vv, vk) for vk, vv in v.items() if is_serializable(vv)
            }
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
    except (TypeError, UnicodeError):
        return False
    return True


def get_meta_iptc(file_stream):
    """Returns the image IPTC metadata in a dictionary of tag:value pairs.

    @param file_stream: stream
    """
    file_stream.seek(0)
    img = Image.open(file_stream)
    iptc_raw = IptcImagePlugin.getiptcinfo(img)
    metadata = {}

    if iptc_raw is None:
        return metadata

    for code, value in iptc_raw.items():
        try:
            tag = iim_codes[code]
        except KeyError:
            continue
        if isinstance(value, list):
            value = [decode(v) for v in value]
        elif isinstance(value, bytes):
            value = decode(value)
        metadata[tag] = value
    return metadata
