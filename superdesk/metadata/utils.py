# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime
from uuid import uuid4
from flask import current_app as app

from superdesk.utils import SuperdeskBaseEnum
from .item import GUID_TAG, GUID_NEWSML, GUID_FIELD, ITEM_TYPE, CONTENT_TYPE
from .packages import PACKAGE_TYPE, TAKES_PACKAGE


item_url = 'regex("[\w,.:_-]+")'

extra_response_fields = [GUID_FIELD, 'headline', 'firstcreated', 'versioncreated', 'archived']

aggregations = {
    'type': {'terms': {'field': 'type'}},
    'desk': {'terms': {'field': 'task.desk', 'size': 0}},
    'category': {'terms': {'field': 'anpa_category.name', 'size': 0}},
    'source': {'terms': {'field': 'source', 'size': 0}},
    'urgency': {'terms': {'field': 'urgency'}},
    'priority': {'terms': {'field': 'priority'}},
    'legal': {'terms': {'field': 'flags.marked_for_legal'}},
    'sms': {'terms': {'field': 'flags.marked_for_sms'}},
    'genre': {'terms': {'field': 'genre.name', 'size': 0}}
}

elastic_highlight_query = {
    'require_field_match': False,
    'pre_tags': ['<span class=\"es-highlight\">'],
    'post_tags': ['</span>'],
    'fields': {
        'body_html': {'number_of_fragments': 0},
        'body_footer': {'number_of_fragments': 0},
        'headline': {'number_of_fragments': 0},
        'slugline': {'number_of_fragments': 0},
        'abstract': {'number_of_fragments': 0}
    }
}


def generate_guid(**hints):
    """Generate a GUID based on given hints

    param: hints: hints used for generating the guid
    """
    newsml_guid_format = 'urn:newsml:%(domain)s:%(timestamp)s:%(identifier)s'
    tag_guid_format = 'tag:%(domain)s:%(year)d:%(identifier)s'

    if not hints.get('id'):
        hints['id'] = str(uuid4())

    if app.config.get('GENERATE_SHORT_GUID', False):
        return hints['id']

    t = datetime.today()

    if hints['type'].lower() == GUID_TAG:
        return tag_guid_format % {'domain': app.config['SERVER_DOMAIN'], 'year': t.year, 'identifier': hints['id']}
    elif hints['type'].lower() == GUID_NEWSML:
        return newsml_guid_format % {'domain': app.config['SERVER_DOMAIN'],
                                     'timestamp': t.isoformat(),
                                     'identifier': hints['id']}
    return None


def generate_tag(domain, id):
    """Generate tag for given domain and id.

    :param domain: domain string
    :param id: local id
    """
    return 'tag:{}:{}'.format(domain, id)


def is_normal_package(doc):
    """
    Returns True if the passed doc is a package and not a takes package. Otherwise, returns False.

    :return: True if it's a Package and not a Takes Package, False otherwise.
    """

    return doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and doc.get(PACKAGE_TYPE, '') != TAKES_PACKAGE


def is_takes_package(doc):
    """
    Returns True if the passed doc is a takes package. Otherwise, returns False.

    :return: True if it's a Takes Package, False otherwise.
    """

    return doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and doc.get(PACKAGE_TYPE, '') == TAKES_PACKAGE


class ProductTypes(SuperdeskBaseEnum):
    API = 'api'
    DIRECT = 'direct'
    BOTH = 'both'
