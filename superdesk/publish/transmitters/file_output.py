# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.publish.publish_service import PublishService, get_file_extension
from superdesk.publish import register_transmitter
from superdesk.errors import PublishFileError

errors = [PublishFileError.fileSaveError().get_error_description()]


class FilePublishService(PublishService):
    def _transmit(self, queue_item, subscriber):
        config = queue_item.get('destination', {}).get('config', {})
        try:
            # use the file extension from config if it is set otherwise use extension for the format
            extension = config.get('file_extension') or get_file_extension(queue_item)
            with open('{}/{}-{}-{}.{}'.format(config['file_path'],
                                              queue_item['item_id'].replace(':', '-'),
                                              str(queue_item.get('item_version', '')),
                                              str(queue_item.get('published_seq_num', '')),
                                              extension), 'wb') as f:
                f.write(queue_item['encoded_item'])
        except Exception as ex:
            raise PublishFileError.fileSaveError(ex, config)


register_transmitter('File', FilePublishService(), errors)
