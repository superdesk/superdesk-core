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

from flask import current_app as app
from superdesk.services import BaseService
from superdesk.utils import ListCursor


logger = logging.getLogger(__name__)


class LanguagesService(BaseService):
    def get(self, req, lookup):
        """
        Return the list of languages defined on config file.
        """

        return ListCursor(app.config.get('LANGUAGES', []))
