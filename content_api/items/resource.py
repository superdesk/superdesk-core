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
from superdesk.metadata.item import metadata_schema, not_analyzed
from content_api import MONGO_PREFIX, ELASTIC_PREFIX

code_mapping = {
    'type': 'object',
    'properties': {
        'name': not_analyzed,
        'code': not_analyzed
    }
}

schema = {
    '_id': metadata_schema['_id'],
    'associations': metadata_schema['associations'],
    'body_html': {'type': 'string'},
    'body_text': {'type': 'string'},
    'byline': {'type': 'string'},
    'copyrightnotice': metadata_schema['copyrightnotice'],
    'copyrightholder': {'type': 'string'},
    'description_html': {'type': 'string'},
    'description_text': {'type': 'string'},
    'headline': {'type': 'string'},
    'language': metadata_schema['language'],
    'located': {'type': 'string'},
    'mimetype': metadata_schema['mimetype'],
    'organization': {'type': 'list'},
    'person': {'type': 'list'},
    'place': {'type': 'list'},
    'profile': {'type': 'string'},
    'pubstatus': metadata_schema['pubstatus'],
    'renditions': {'type': 'dict'},
    'service': {'type': 'list', 'mapping': code_mapping},
    'slugline': {'type': 'string'},
    'source': metadata_schema['source'],
    'subject': {'type': 'list', 'mapping': code_mapping},
    'keywords': metadata_schema['keywords'],
    'type': metadata_schema['type'],
    'urgency': {'type': 'integer'},
    'priority': {'type': 'integer'},
    'uri': metadata_schema['guid'],  # we use guid value for uri, so index it in a same way
    'usageterms': {'type': 'string'},
    'version': {'type': 'string', 'required': True, 'empty': False, 'nullable': False},
    'versioncreated': {'type': 'datetime', 'required': True},
    'firstcreated': {'type': 'datetime'},
    'evolvedfrom': Resource.not_analyzed_field(),
    'subscribers': Resource.not_analyzed_field('list'),
    'ednote': {'type': 'string'},
    'signal': {
        'type': 'list',
        'mapping': {
            'type': 'object',
            'properties': {
                'code': not_analyzed,
                'name': not_analyzed,
                'scheme': not_analyzed
            }
        }
    },
    'genre': {'type': 'list', 'mapping': code_mapping},
    'ancestors': Resource.not_analyzed_field('list'),
}


class ItemsResource(Resource):
    """A class defining and configuring the /items API endpoint."""

    # Example of an ID of an object in database (whitout quotes):
    #
    #     "tag:example.com,0000:newsml_BRE9A605"
    #     "tag:localhost:2015:f4b35e12-559b-4a2b-b1f2-d5e64048bde8"
    #
    item_url = 'regex("[\w,.:-]+")'
    schema = schema

    datasource = {
        'search_backend': 'elastic',
        'elastic_filter': {"bool": {"must_not": {"term": {"type": "composite"}}}},
        'default_sort': [('_updated', -1)]
    }

    item_methods = ['GET']
    resource_methods = ['GET']
    versioning = True
    mongo_prefix = MONGO_PREFIX
    elastic_prefix = ELASTIC_PREFIX
