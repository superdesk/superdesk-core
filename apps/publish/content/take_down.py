# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .common import BasePublishResource, ITEM_TAKEDOWN, ITEM_KILL
from .kill import KillPublishService
from superdesk.metadata.item import CONTENT_STATE
import logging

logger = logging.getLogger(__name__)


class TakeDownPublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, ITEM_TAKEDOWN)


class TakeDownPublishService(KillPublishService):
    publish_type = ITEM_KILL
    published_state = CONTENT_STATE.RECALLED
    item_operation = ITEM_TAKEDOWN

    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource=datasource, backend=backend)
