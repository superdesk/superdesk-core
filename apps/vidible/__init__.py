# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import logging

import superdesk
from .vidible import bp

logger = logging.getLogger(__name__)


def init_app(app):
    superdesk.blueprint(bp, app)
