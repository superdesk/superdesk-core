# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.services import BaseService
import superdesk.metadata.utils
import datetime
import superdesk


class DataUpdatesResource(Resource):
    schema = {"name": {"type": "string", "required": True}, "applied": {"type": "datetime", "required": True}}
    internal_resource = True
    item_url = superdesk.metadata.utils.item_url


class DataUpdatesService(BaseService):
    def on_create(self, docs):
        for doc in docs:
            doc["applied"] = datetime.datetime.now()


def init_app(app):
    endpoint_name = "data_updates"
    service = DataUpdatesService(endpoint_name, backend=superdesk.get_backend())
    DataUpdatesResource(endpoint_name, app=app, service=service)
