# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import logging.config
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('superdesk')


def item_msg(msg, item):
    """Return a message with item id appended.

    :param msg: Original message
    :param item: Item object
    """
    return '{} item={}'.format(msg, str(item.get('_id', item.get('guid'))))


def configure_logging(file_path):
    """
    configure logging.
    :param str file_path:
    """
    try:
        logging_conf = open(file_path, 'r')
        logging_dict = yaml.load(logging_conf)
        logging.config.dictConfig(logging_dict)
    except:
        logger.error('Cannot load logging config. File: {}'.format(file_path))
