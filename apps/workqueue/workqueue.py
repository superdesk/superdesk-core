# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from superdesk.metadata.item import get_schema


class WorkqueueResource(superdesk.Resource):
    endpoint_name = "workqueue"
    datasource = {"source": "archive"}
    schema = get_schema()
    item_methods = ["GET"]


class WorkqueueService(superdesk.Service):

    pass
