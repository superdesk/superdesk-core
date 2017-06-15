# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from __future__ import absolute_import
from PIL import Image
from io import BytesIO
import logging
from copy import deepcopy
from flask import current_app as app
from .media_operations import process_file_from_stream
from .media_operations import crop_image
from .media_operations import download_file_from_url
from .media_operations import process_file
from .image import fix_orientation
from eve.utils import config
from superdesk import get_resource_service
from superdesk.filemeta import set_filemeta


logger = logging.getLogger(__name__)


def generate_renditions(original, media_id, inserted, file_type, content_type,
                        rendition_config, url_for_media, insert_metadata=True):
    """Generate system renditions for given media file id.

    :param BytesIO original: original image byte stream
    :param str media_id: media id
    :param list inserted: list of media ids inserted
    :param str file_type: file_type
    :param str content_type: content type
    :param dict rendition_config: rendition config
    :param url_for_media: function to generate url
    :param bool insert_metadata: boolean to inserted metadata or not. For AWS storage it is false.
    :return: dict of renditions
    """
    rend = {'href': app.media.url_for_media(media_id, content_type), 'media': media_id, 'mimetype': content_type}
    renditions = {'original': rend}

    if file_type != 'image':
        return renditions

    original.seek(0)
    img = Image.open(original)
    width, height = img.size
    rend.update({'width': width})
    rend.update({'height': height})

    # remove crop if original is small
    custom_renditions = get_renditions_spec(without_internal_renditions=True)
    for rendition, crop in custom_renditions.items():
        if not can_generate_custom_crop_from_original(width, height, crop):
            rendition_config.pop(rendition, None)

    ext = content_type.split('/')[1].lower()
    if ext in ('JPG', 'jpg'):
        ext = 'jpeg'
    ext = ext if ext in ('jpeg', 'gif', 'tiff', 'png') else 'png'
    for rendition, rsize in rendition_config.items():
        cropping_data = {}
        # reset
        original.seek(0)
        fix_orientation(original)
        # create the rendition (can be based on ratio or pixels)
        if rsize.get('width') or rsize.get('height'):
            resized, width, height = _resize_image(original, (rsize.get('width'), rsize.get('height')), ext)
        elif rsize.get('ratio'):
            resized, width, height, cropping_data = _crop_image(original, ext, rsize.get('ratio'))
        rend_content_type = 'image/%s' % ext
        file_name, rend_content_type, metadata = process_file_from_stream(resized, content_type=rend_content_type)
        resized.seek(0)
        _id = app.media.put(resized, filename=file_name,
                            content_type=rend_content_type,
                            metadata=metadata if insert_metadata else None)
        inserted.append(_id)
        renditions[rendition] = {'href': url_for_media(_id, rend_content_type), 'media': _id,
                                 'mimetype': 'image/%s' % ext, 'width': width, 'height': height}
        # add the cropping data if exist
        renditions[rendition].update(cropping_data)
    return renditions


def can_generate_custom_crop_from_original(width, height, crop):
    """Checks whether custom crop can be generated or not

    :param int width: width of original
    :param int height: height of original
    :param dict crop: custom crop data
    :return bool: True if custom crop is within original image dimensions
    """
    if not crop:
        crop = {}

    if crop.get('ratio'):
        return True

    try:
        crop_width = int(crop['width'])
    except (KeyError, TypeError, ValueError):
        crop_width = None

    try:
        crop_height = int(crop['height'])
    except (KeyError, TypeError, ValueError):
        crop_height = None

    if crop_width is None and crop_height is None:
        return False

    if (crop_width is not None and crop_height is None) or (crop_width is None and crop_height is not None):
        return True

    return width >= crop_width and height >= crop_height


def delete_file_on_error(doc, file_id):
    # Don't delete the file if we are on the import from storage flow
    if doc.get('_import', None):
        return
    app.media.delete(file_id)


def _crop_image(content, format, ratio):
    """Crop the image given as a binary stream

    @param content: stream
        The binary stream containing the image
    @param format: str
        The format of the resized image (e.g. png, jpg etc.)
    @param ratio: string, int or float
        Ratio to apply. '16:9', '1:1' etc...
    @return: stream
        Returns the resized image as a binary stream.
    """
    img = Image.open(content)
    width, height = img.size
    if type(ratio) not in [float, int]:
        ratio = ratio.split(':')
        ratio = int(ratio[0]) / int(ratio[1])
    if height * ratio > width:
        new_width = width
        new_height = int(new_width / ratio)
        cropping_data = {
            'CropLeft': 0,
            'CropRight': new_width,
            'CropTop': int((height - new_height) / 2),
            'CropBottom': int((height - new_height) / 2) + new_height,
        }
    else:
        new_width = int(height * ratio)
        new_height = height
        cropping_data = {
            'CropLeft': int((width - new_width) / 2),
            'CropRight': int((width - new_width) / 2) + new_width,
            'CropTop': 0,
            'CropBottom': new_height,
        }
    crop, out = crop_image(content, file_name='crop.for.rendition', cropping_data=cropping_data, image_format=format)
    return out, new_width, new_height, cropping_data


def to_int(x):
    """Try to convert x to int."""
    try:
        return int(x)
    except TypeError:
        return x


def _resize_image(content, size, format='png', keepProportions=True):
    """Resize the image given as a binary stream

    @param content: stream
        The binary stream containing the image
    @param format: str
        The format of the resized image (e.g. png, jpg etc.)
    @param size: tuple
        A tuple of width, height
    @param keepProportions: boolean
        If true keep image proportions; it will adjust the resized
        image size.
    @return: stream
        Returns the resized image as a binary stream.
    """
    assert isinstance(size, tuple)
    img = Image.open(content)
    width, height = img.size
    new_width, new_height = [to_int(x) for x in size]
    if keepProportions:
        if new_width is None and new_height is None:
            raise Exception('size parameter requires at least width or height value')
        # resize with width and height
        if new_width is not None and new_height is not None:
            new_width, new_height = new_width, new_height
            x_ratio = width / new_width
            y_ratio = height / new_height
            if x_ratio > y_ratio:
                new_height = int(height / x_ratio)
            else:
                new_width = int(width / y_ratio)
        # resize with only one dimension
        else:
            original_ratio = width / height
            if new_width is not None:
                new_height = int(int(new_width) / original_ratio)
            else:
                new_width = int(new_height * original_ratio)
    resized = img.resize((new_width, new_height), Image.ANTIALIAS)
    out = BytesIO()
    resized.save(out, format, quality=85)
    out.seek(0)
    return out, new_width, new_height


def get_renditions_spec(without_internal_renditions=False, no_custom_crops=False):
    """Return the list of the needed renditions.

    It contains the ones defined in settings in `RENDITIONS.picture`
    and the ones defined in vocabularies in `crop_sizes`

    @return: list
        Returns the list of renditions specification.
    """
    rendition_spec = {}
    # renditions required by superdesk
    if not without_internal_renditions:
        rendition_spec = deepcopy(config.RENDITIONS['picture'])

    if not no_custom_crops:
        # load custom renditions sizes
        custom_crops = get_resource_service('vocabularies').find_one(req=None, _id='crop_sizes')
        if custom_crops:
            for crop in custom_crops.get('items'):
                # complete list of wanted renditions
                rendition_spec[crop['name']] = crop
    return rendition_spec


def update_renditions(item, href, old_item):
    """Update renditions for an item.

    If the old_item has renditions uploaded in to media then the old rendition details are
    assigned to the item, this avoids repeatedly downloading the same image and leaving the media entries orphaned.
    If there is no old_item the original is downloaded and renditions are
    generated.
    :param item: parsed item from source
    :param href: reference to original
    :param old_item: the item that we have already ingested, if it exists
    :return: item with renditions
    """
    inserted = []
    try:
        # If there is an existing set of renditions we keep those
        if old_item:
            media = old_item.get('renditions', {}).get('original', {}).get('media', {})
            if media:
                item['renditions'] = old_item['renditions']
                item['mimetype'] = old_item.get('mimetype')
                item['filemeta'] = old_item.get('filemeta')
                item['filemeta_json'] = old_item.get('filemeta_json')
                return

        content, filename, content_type = download_file_from_url(href)
        file_type, ext = content_type.split('/')
        metadata = process_file(content, file_type)
        file_guid = app.media.put(content, filename, content_type, metadata)
        inserted.append(file_guid)
        rendition_spec = get_renditions_spec()
        renditions = generate_renditions(content, file_guid, inserted, file_type,
                                         content_type, rendition_spec, app.media.url_for_media)
        item['renditions'] = renditions
        item['mimetype'] = content_type
        set_filemeta(item, metadata)
    except Exception as e:
        logger.exception(e)
        for file_id in inserted:
            app.media.delete(file_id)
        raise
