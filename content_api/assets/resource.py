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


class AssetsResource(Resource):
    schema = {
        'media_id': {'type': 'string', 'required': True},
        'URL': {'type': 'string'},
        'media': {'type': 'file'},
        'mime_type': {'type': 'string'},
        'filemeta': {'type': 'dict'}
    }
    item_methods = ['GET']
    resource_methods = ['GET', 'POST']
