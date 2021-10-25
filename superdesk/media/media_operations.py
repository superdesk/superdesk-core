# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import arrow
import magic
import base64
import hashlib
import logging
import requests
import requests.exceptions
import os

from urllib.parse import urljoin
from bson import ObjectId
from io import BytesIO
from PIL import Image, ImageEnhance
from flask import json, url_for
from .image import get_meta
from .video import get_meta as video_meta
from superdesk.errors import SuperdeskApiError
from flask import current_app as app
from mimetypes import guess_extension

logger = logging.getLogger(__name__)


def hash_file(afile, hasher, blocksize=65536):
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()


def get_file_name(file):
    return hash_file(file, hashlib.sha256())


def fix_content_type(content_type, content):
    """Get known content_type

    It will try to get it from content if it starts with application or is unknown.
    """
    if not content_type or "application/" in content_type:
        content_type = magic.from_buffer(content.getvalue(), mime=True)
        content.seek(0)
    return str(content_type)


def download_file_from_url(url, request_kwargs=None):
    """Download file from given url.

    In case url is relative it will prefix it with current host.

    :param url: file url
    """

    if not request_kwargs:
        request_kwargs = {}

    try:
        rv = requests.get(url, headers={"User-Agent": "Superdesk-1.0"}, timeout=(5, 25), **request_kwargs)
    except requests.exceptions.MissingSchema:  # any route will do here, we only need host
        rv = requests.get(urljoin(url_for("static", filename="x", _external=True), url), timeout=15, **request_kwargs)
    if rv.status_code not in (200, 201):
        raise SuperdeskApiError.internalError("Failed to retrieve file from URL: %s" % url)
    content = BytesIO(rv.content)
    content_type = rv.headers.get("content-type", "image/jpeg").split(";")[0]
    content_type = fix_content_type(content_type, content)
    ext = str(content_type).split("/")[1]
    name = str(ObjectId()) + ext
    return content, name, content_type


def download_file_from_encoded_str(encoded_str):
    content = encoded_str.split(";base64,")
    mime = content[0].split(":")[1]
    ext = content[0].split("/")[1]
    name = str(ObjectId()) + ext
    content = base64.b64decode(content[1])
    return BytesIO(content), name, mime


def process_file_from_stream(content, content_type=None):
    content_type = content_type or content.content_type
    content = BytesIO(content.read())
    content_type = fix_content_type(content_type, content)
    file_type, ext = content_type.split("/")
    try:
        metadata = process_file(content, file_type)
    except OSError:  # error from PIL when image is supposed to be an image but is not.
        raise SuperdeskApiError.internalError("Failed to process file")
    file_name = get_file_name(content)
    content.seek(0)
    metadata = encode_metadata(metadata)
    metadata.update({"length": json.dumps(len(content.getvalue()))})
    return file_name, content_type, metadata


def encode_metadata(metadata):
    return dict((k.lower(), json.dumps(v)) for k, v in metadata.items())


def decode_metadata(metadata):
    return dict((k.lower(), decode_val(v)) for k, v in metadata.items())


def decode_val(string_val):
    """Format dates that elastic will try to convert automatically."""
    val = json.loads(string_val)
    try:
        arrow.get(val, "YYYY-MM-DD")  # test if it will get matched by elastic
        return str(arrow.get(val))
    except (Exception):
        return val


def process_file(content, type):
    """Retrieves the media file metadata

    :param BytesIO content: content stream
    :param str type: type of media file
    :return: dict metadata related to media file.
    """
    if type == "image":
        return process_image(content)
    if type in ("audio", "video"):
        return process_video(content)
    return {}


def process_video(content):
    """Retrieves the video/audio metadata

    :param BytesIO content: content stream
    :return: dict video/audio metadata
    """
    content.seek(0)
    meta = video_meta(content)
    content.seek(0)
    return meta


def process_image(content):
    """Retrieves the image metadata

    :param BytesIO content: content stream
    :return: dict image metadata
    """
    content.seek(0)
    meta = get_meta(content)
    content.seek(0)
    return meta


def _get_cropping_data(doc):
    """Get PIL Image crop data from doc with superdesk crops specs.

    :param doc: crop dict
    """
    if all(
        [
            doc.get("CropTop", None) is not None,
            doc.get("CropLeft", None) is not None,
            doc.get("CropRight", None) is not None,
            doc.get("CropBottom", None) is not None,
        ]
    ):
        return (int(doc["CropLeft"]), int(doc["CropTop"]), int(doc["CropRight"]), int(doc["CropBottom"]))


def crop_image(content, file_name, cropping_data, exact_size=None, image_format=None):
    """Crop image stream to given crop.

    :param content: image file stream
    :param file_name
    :param cropping_data: superdesk crop dict ({'CropLeft': 0, 'CropTop': 0, ...})
    :param exact_size: dict with `width` and `height` values
    """
    if not isinstance(cropping_data, tuple):
        cropping_data = _get_cropping_data(cropping_data)
    if cropping_data:
        logger.debug("Opened image {} from stream, going to crop it".format(file_name))
        content.seek(0)
        img = Image.open(content)
        cropped = img.crop(cropping_data)
        if exact_size and "width" in exact_size and "height" in exact_size:
            cropped = cropped.resize((int(exact_size["width"]), int(exact_size["height"])), Image.ANTIALIAS)
        logger.debug("Cropped image {} from stream, going to save it".format(file_name))
        try:
            out = BytesIO()
            cropped.save(out, image_format or img.format)
            out.seek(0)
            setattr(out, "width", cropped.size[0])
            setattr(out, "height", cropped.size[1])
            return True, out
        except Exception as io:
            logger.exception("Failed to generate crop for filename: {}. Crop: {}".format(file_name, cropping_data))
            return False, io
    return False, content


def get_watermark(image):
    """Apply the specified watermark to the image if available

    :param image:
    :return: watermarked image
    """
    image = image.copy()
    if not app.config.get("WATERMARK_IMAGE"):
        return image
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    path = os.path.join(app.config["ABS_PATH"], app.config["WATERMARK_IMAGE"])
    if not os.path.isfile(path):
        logger.warning("No water mark file found at : {}".format(path))
        return image
    with open(path, mode="rb") as watermark_binary:
        watermark_image = Image.open(watermark_binary)
        set_opacity(watermark_image, 0.3)
        watermark_layer = Image.new("RGBA", image.size)
        watermark_layer.paste(
            watermark_image,
            (
                image.size[0] - watermark_image.size[0],
                int((image.size[1] - watermark_image.size[1]) * 0.66),
            ),
        )

    watermark = Image.alpha_composite(image, watermark_layer)
    return watermark.convert("RGB")


def set_opacity(image, opacity=1):
    alpha = image.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    image.putalpha(alpha)


def guess_media_extension(content_type):
    ext = str(guess_extension(content_type))
    if ext in [".jpe", ".jpeg"]:
        return ".jpg"
    if "mp3" in content_type or "audio/mpeg" in content_type:
        return ".mp3"
    if "flac" in content_type:
        return ".flac"
    return ext if ext != "None" else ""
