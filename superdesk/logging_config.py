# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import yaml
import logging

from logging.config import dictConfig


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('superdesk')

# set default levels
logging.getLogger('ldap3').setLevel(logging.WARNING)
logging.getLogger('kombu').setLevel(logging.WARNING)
logging.getLogger('elasticsearch').setLevel(logging.ERROR)

logging.getLogger('apps').setLevel(logging.INFO)
logging.getLogger('superdesk').setLevel(logging.INFO)
logging.getLogger('superdesk.websockets_comms').setLevel(logging.WARNING)


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
        dictConfig(logging_dict)
    except (FileNotFoundError, yaml.MarkedYAMLError):
        logger.warn('Cannot load logging config. File: %s', file_path)
