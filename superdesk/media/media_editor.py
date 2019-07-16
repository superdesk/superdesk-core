# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.resource import Resource, not_analyzed
from superdesk.services import BaseService
from superdesk.media.renditions import generate_renditions, get_renditions_spec
from superdesk import get_resource_service
from superdesk import errors
from flask import current_app
from PIL import Image, ImageEnhance
from io import BytesIO
from eve.utils import config
import os.path
import uuid
import logging

logger = logging.getLogger(__name__)


class MediaEditorResource(Resource):
    schema = {
        'item_id': {
            'type': 'string',
            'mapping': not_analyzed
        },
        'item': {
            'type': 'dict',
            'mapping': not_analyzed
        },
        'edit': {
            'type': 'dict',
            'required': True,
            'mapping': not_analyzed
        }
    }
    internal_resource = False
    resource_methods = ['POST']
    item_methods = []
    privileges = {'POST': 'archive'}


class MediaEditorService(BaseService):
    """Service givin metadata on backend itself"""

    def transform(self, im, operation, param):
        """Apply image transformation

        :param Image im: image to transform
        :param str operation: name of the operation to do
        :param param: parameters of the operation
        :return Image: resulting image
        """
        if operation == 'rotate':
            return im.rotate(int(param), expand=1)

        elif operation == 'flip':
            if param in ('vertical', 'both'):
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
            if param in ('horizontal', 'both'):
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            return im

        elif operation == 'brightness':
            return ImageEnhance.Brightness(im).enhance(float(param))

        elif operation == 'contrast':
            return ImageEnhance.Contrast(im).enhance(float(param))

        elif operation == 'grayscale':
            return im.convert('L')

        elif operation == 'saturation':
            return ImageEnhance.Color(im).enhance(float(param))

        logger.warning('unhandled operation: {operation} {param}'.format(
            operation=operation,
            param=param))

        return im

    def create(self, docs):
        """Apply transformation requested in 'edit'"""
        ids = []
        archive = get_resource_service('archive')
        for doc in docs:
            # first we get item and requested edit operations
            item = doc.pop('item', None)
            if item is None:
                try:
                    item_id = doc.pop('item_id')
                except KeyError:
                    raise errors.SuperdeskApiError.badRequestError('either item or item_id must be specified')
            else:
                item_id = item[config.ID_FIELD]

            if item is None and item_id:
                item = next(archive.find({'_id': item_id}))
            edit = doc.pop('edit')

            # now we retrieve and load current original media
            rendition = item['renditions']['original']
            media_id = rendition['media']
            media = current_app.media.get(media_id)
            out = im = Image.open(media)

            # we apply all requested operations on original media
            for operation, param in edit.items():
                try:
                    out = self.transform(out, operation, param)
                except ValueError:
                    # if the operation can't be applied just ignore it
                    logger.warning('failed to apply operation: {operation} {param} for media {id}'.format(
                        operation=operation,
                        param=param,
                        id=media_id))
            buf = BytesIO()
            out.save(buf, format=im.format)

            # we set metadata
            buf.seek(0)
            content_type = rendition['mimetype']
            ext = os.path.splitext(rendition['href'])[1]
            filename = str(uuid.uuid4()) + ext

            # and save transformed media in database
            media_id = current_app.media.put(buf, filename=filename, content_type=content_type)

            # now we recreate other renditions based on transformed original media
            buf.seek(0)
            renditions = generate_renditions(buf,
                                             media_id,
                                             [],
                                             'image',
                                             content_type,
                                             get_renditions_spec(),
                                             current_app.media.url_for_media)

            ids.append(item_id)
            doc['renditions'] = renditions

        return [ids]
