# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import Resource


class MediaReferencesResource(Resource):
    schema = {
        # item where media belongs i.e. in case of picture item it will be picture item
        # in case of associated featuremedia it will be the parent item id.
        'item_id': {
            'type': 'string',
            'required': True
        },
        # media of the renditions
        'media_id': {
            'type': 'string',
            'required': True
        },
        # associated item id
        'associated_id': {
            'type': 'string',
            'nullable': True
        },
        'published': {
            'type': 'boolean'
        }
    }
    endpoint_name = 'media_references'
    internal_resource = False
    resource_methods = ['GET']
    item_methods = ['GET']
    mongo_indexes = {
        'item_id_1_media_1': [('item_id', 1), ('media_id', 1)],
        'media_1': [('media_id', 1)],
        'associated_id': [('associated_id', 1)]
    }
    query_objectid_as_string = True
