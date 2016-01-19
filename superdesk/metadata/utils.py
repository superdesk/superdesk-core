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
from .item import GUID_TAG, GUID_NEWSML, GUID_FIELD, ITEM_TYPE, CONTENT_TYPE
from .packages import PACKAGE_TYPE, TAKES_PACKAGE


item_url = 'regex("[\w,.:_-]+")'

extra_response_fields = [GUID_FIELD, 'headline', 'firstcreated', 'versioncreated', 'archived']

aggregations = {
    'type': {'terms': {'field': 'type'}},
    'desk': {'terms': {'field': 'task.desk', 'size': 0}},
    'stage': {'terms': {'field': 'task.stage', 'size': 0}},
    'category': {'terms': {'field': 'anpa_category.name', 'size': 0}},
    'source': {'terms': {'field': 'source', 'size': 0}},
    'state': {'terms': {'field': 'state'}},
    'urgency': {'terms': {'field': 'urgency'}},
    'priority': {'terms': {'field': 'priority'}},
    'legal': {'terms': {'field': 'flags.marked_for_legal'}},
    'keywords': {'terms': {'field': 'keywords', 'size': 0}},
    'genre': {'terms': {'field': 'genre.name', 'size': 0}},
    'day': {'date_range': {'field': 'firstcreated', 'format': 'dd-MM-yyy HH:mm:ss', 'ranges': [{'from': 'now-24H'}]}},
    'week': {'date_range': {'field': 'firstcreated', 'format': 'dd-MM-yyy HH:mm:ss', 'ranges': [{'from': 'now-1w'}]}},
    'month': {'date_range': {'field': 'firstcreated', 'format': 'dd-MM-yyy HH:mm:ss', 'ranges': [{'from': 'now-1M'}]}},
}


def generate_guid(**hints):
    """
    Generate a GUID based on given hints
    param: hints: hints used for generating the guid
    """
    newsml_guid_format = 'urn:newsml:%(domain)s:%(timestamp)s:%(identifier)s'
    tag_guid_format = 'tag:%(domain)s:%(year)d:%(identifier)s'

    if not hints.get('id'):
        hints['id'] = str(uuid4())

    t = datetime.today()

    if hints['type'].lower() == GUID_TAG:
        return tag_guid_format % {'domain': app.config['SERVER_DOMAIN'], 'year': t.year, 'identifier': hints['id']}
    elif hints['type'].lower() == GUID_NEWSML:
        return newsml_guid_format % {'domain': app.config['SERVER_DOMAIN'],
                                     'timestamp': t.isoformat(),
                                     'identifier': hints['id']}
    return None


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
