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
from eve.utils import config


class ApiAuditService(BaseService):
    """
    Service class that provides an auditing service for the retrieval of items, assets and packages via the API
    """

    def audit_item(self, item, id):
        """
        Record the retrieval of an item or asset
        :param item: The item to audit
        :param id: id of the item
        :return:
        """
        subscriber = getattr(g, 'user', None)
        # in behave testing we get user (dict)
        if isinstance(subscriber, dict):
            subscriber = subscriber.get(config.ID_FIELD)

        audit = {
            'type': item.get('type', ''),
            'subscriber': subscriber,
            'uri': item.get('uri', None),
            'items_id': id,
            'version': item.get('version', ''),
            'remote_addr': request.remote_addr
        }
        self.post([audit])
