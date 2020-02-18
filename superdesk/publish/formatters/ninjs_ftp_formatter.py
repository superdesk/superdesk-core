# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from .ninjs_formatter import NINJSFormatter
from superdesk.media.renditions import get_rendition_file_name


class FTPNinjsFormatter(NINJSFormatter):
    def __init__(self):
        super().__init__()
        self.format_type = 'ftp ninjs'
        self.internal_renditions = []

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        """
        Re-wire that href's in the document to be relative to the destination FTP server root, it expects the
        destination to be an FTP server
        :param article:
        :param subscriber:
        :param recursive:
        :return:
        """

        include_original = subscriber.get('destinations')[0].get('config').get('include_original', False)
        if include_original:
            self.internal_renditions = ['original']

        ninjs = super()._transform_to_ninjs(article, subscriber, recursive)

        # Get the path that the renditions will be pushed to
        path = subscriber.get('destinations')[0].get('config').get('associated_path')

        if path:
            renditions = ninjs.get('renditions')
            if renditions:
                for name, rendition in renditions.items():
                    rendition['href'] = '/' + path.lstrip('/') + (
                        '/' if not path.endswith('/') else '') + get_rendition_file_name(rendition)

        return ninjs
