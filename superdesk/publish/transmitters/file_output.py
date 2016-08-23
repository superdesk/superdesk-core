# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.publish.publish_service import PublishService
from superdesk.publish import register_transmitter
from superdesk.errors import PublishFileError
from os import path

errors = [PublishFileError.fileSaveError().get_error_description()]


class FilePublishService(PublishService):
    def _transmit(self, queue_item, subscriber):
        try:
            config = queue_item['destination']['config']
            file_path = config['file_path']
            if not path.isabs(file_path):
                file_path = "/" + file_path
            with open(path.join(file_path, PublishService.get_filename(queue_item)), 'wb') as f:
                f.write(queue_item['encoded_item'])
        except Exception as ex:
            raise PublishFileError.fileSaveError(ex, config)


register_transmitter('File', FilePublishService(), errors)
