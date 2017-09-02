# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource

from eve.utils import config
from superdesk.metadata.utils import item_url


class SystemSettingsResource(Resource):
    item_url = item_url
    schema = {
        config.ID_FIELD: {
            'type': 'string',
            'required': True,
            'unique': True
        },
        'type': {
            'type': 'string',
            'required': True,
            'allowed': ['string', 'integer', 'timedelta']
        },
        'value': {
            'required': True
        }
    }
    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'PATCH', 'PUT']
    privileges = {'POST': 'system_settings', 'PATCH': 'system_settings', 'PUT': 'system_settings',
                  'DELETE': 'system_settings'}
