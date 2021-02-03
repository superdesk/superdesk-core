# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from content_api import MONGO_PREFIX

schema = {
    "type": {"type": "string"},
    "subscriber": {"type": "string"},
    "uri": {"type": "string"},
    "items_id": {"type": "string"},
    "version": {"type": "string"},
    "remote_addr": {"type": "string"},
}


class ApiAuditResource(Resource):
    """
    Resource class for the auditing of the API
    """

    schema = schema
    mongo_prefix = MONGO_PREFIX
    internal_resource = True
    mongo_indexes = {"subscriber": [("subscriber", 1)]}
