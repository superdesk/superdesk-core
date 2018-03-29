# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers import FileFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.errors import ParserError
from superdesk.media.media_operations import process_file_from_stream
from superdesk.media.image import get_meta_iptc
from superdesk.media.iim_codes import TAG
from superdesk.metadata.item import GUID_TAG, ITEM_TYPE, CONTENT_TYPE
from superdesk.metadata import utils
from superdesk.media.renditions import generate_renditions, get_renditions_spec
from superdesk.upload import url_for_media
from superdesk import filemeta
from flask import current_app as app
from eve.utils import config
from datetime import datetime
import dateutil.parser
import mimetypes
import logging
import os.path

logger = logging.getLogger(__name__)

IPTC_MAPPING = {
    TAG.HEADLINE: 'headline',
    TAG.BY_LINE: 'byline',
    TAG.OBJECT_NAME: 'slugline',
    TAG.CAPTION_ABSTRACT: 'description_text',
    TAG.KEYWORDS: 'keywords',
    TAG.SPECIAL_INSTRUCTIONS: 'ednote',
    TAG.COPYRIGHT_NOTICE: 'copyrightnotice',
    TAG.ORIGINAL_TRANSMISSION_REFERENCE: 'assignment_id'}


class ImageIPTCFeedParser(FileFeedParser):
    """
    Feed Parser which can parse images using IPTC metadata
    """

    NAME = 'image_iptc'
    label = "Image (IPTC metadata)"
    ALLOWED_EXT = mimetypes.guess_all_extensions('image/jpeg')

    def can_parse(self, image_path):
        if not isinstance(image_path, str):
            return False
        return mimetypes.guess_type(image_path)[0] == 'image/jpeg'

    def parse(self, image_path, provider=None):
        try:
            item = self.parse_item(image_path)
            return item
        except Exception as ex:
            raise ParserError.parseFileError(exception=ex, provider=provider)

    def parse_item(self, image_path):
        filename = os.path.basename(image_path)
        content_type = mimetypes.guess_type(image_path)[0]
        guid = utils.generate_guid(type=GUID_TAG)
        item = {'guid': guid,
                config.VERSION: 1,
                config.ID_FIELD: guid,
                ITEM_TYPE: CONTENT_TYPE.PICTURE,
                'mimetype': content_type,
                'versioncreated': datetime.now()
                }
        with open(image_path, 'rb') as f:
            _, content_type, file_metadata = process_file_from_stream(f, content_type=content_type)
            f.seek(0)
            file_id = app.media.put(f, filename=filename, content_type=content_type, metadata=file_metadata)
            filemeta.set_filemeta(item, file_metadata)
            f.seek(0)
            metadata = get_meta_iptc(f)
            f.seek(0)
            rendition_spec = get_renditions_spec(no_custom_crops=True)
            renditions = generate_renditions(f, file_id, [file_id], 'image',
                                             content_type, rendition_spec, url_for_media)
            item['renditions'] = renditions

        try:
            date_created, time_created = metadata[TAG.DATE_CREATED], metadata[TAG.TIME_CREATED]
        except KeyError:
            pass
        else:
            # we format proper ISO 8601 date so we can parse it with dateutil
            datetime_created = '{}-{}-{}T{}:{}:{}{}{}:{}'.format(date_created[0:4],
                                                                 date_created[4:6],
                                                                 date_created[6:8],
                                                                 time_created[0:2],
                                                                 time_created[2:4],
                                                                 time_created[4:6],
                                                                 time_created[6],
                                                                 time_created[7:9],
                                                                 time_created[9:])
            item['firstcreated'] = dateutil.parser.parse(datetime_created)

        # now we map IPTC metadata to superdesk metadata
        for source_key, dest_key in IPTC_MAPPING.items():
            try:
                item[dest_key] = metadata[source_key]
            except KeyError:
                continue
        return item


register_feed_parser(ImageIPTCFeedParser.NAME, ImageIPTCFeedParser())
