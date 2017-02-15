# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.services import BaseService
from flask import g, request


class ApiAuditService(BaseService):
    """
    Service class that provides an auditing service for the retrieval of items, assets and packages via the API
    """

    def post(self, docs, **kwargs):
        subscriber = getattr(g, 'user', None)
        audit = {
            'type': docs.get('type', ''),
            'subscriber': subscriber,
            'uri': docs.get('uri', None),
            'items_id': kwargs.get('id', None),
            'version': docs.get('version', ''),
            'remote_addr': request.remote_addr
        }
        super().post([audit])
