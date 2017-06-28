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

# set default levels
logging.getLogger('ldap3').setLevel(logging.WARNING)
logging.getLogger('kombu').setLevel(logging.WARNING)
logging.getLogger('elasticsearch').setLevel(logging.ERROR)

logging.getLogger('apps').setLevel(logging.INFO)
logging.getLogger('superdesk').setLevel(logging.INFO)
logging.getLogger('superdesk.websockets_comms').setLevel(logging.WARNING)


def item_msg(msg, item):
    """Return a message with item id appended.

    :param msg: Original message
    :param item: Item object
    """
    return '{} item={}'.format(msg, str(item.get('_id', item.get('guid'))))


def configure_logging(file_path):
    """
    Configure logging.

    :param str file_path:
    """
    if not file_path:
        return

    try:
        with open(file_path, 'r') as f:
            logging_dict = yaml.load(f)

        logging.config.dictConfig(logging_dict)
    except:
        logger.warn('Cannot load logging config. File: %s', file_path)
