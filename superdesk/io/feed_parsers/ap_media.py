# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import hashlib
import datetime
import re
from superdesk.utc import utc
import json
from copy import deepcopy
from superdesk import etree as sd_etree
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import FeedParser
from superdesk.io.iptc import subject_codes
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_TAG, Priority
from superdesk.metadata.utils import generate_guid
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, ITEM_URGENCY, ITEM_PRIORITY
from apps.archive.common import format_dateline_to_locmmmddsrc
from superdesk.utc import get_date
from flask import current_app as app
from superdesk import get_resource_service


logger = logging.getLogger(__name__)


class APMediaFeedParser(FeedParser):

    NAME = 'ap_media'

    label = 'AP Media API'

    direct_copy_properties = ('version', 'type', ITEM_URGENCY, 'uri', 'language', 'pubstatus', 'ednote', 'headline',
                              'slugline', 'copyrightnotice')

    # Mapping the received urgensy field to a priority value
    priority_map = {1: Priority.Flash.value,  # Flash
                    2: Priority.Three_Paragraph.value,  # Bulletin
                    3: Priority.Urgent.value,  # Urgent
                    4: Priority.Ordinary.value,  # Routine
                    5: Priority.Ordinary.value,  # Daily
                    6: Priority.Ordinary.value,  # Release at will
                    7: Priority.Ordinary.value,  # Weekday advance
                    8: Priority.Ordinary.value}  # Weekend advance

    slug_code_map = {  # Basketball
                       'BKC-': '15008000', 'BKL-': '15008000', 'BKN-': '15008000',
                       'BKW-': '15008000', 'BKO-': '15008000',
                       # Baseball
                       'BBA-': '15007000', 'BBC-': '15007000', 'BBM-': '15007000', 'BBN-': '15007000',
                       'BBO-': '15007000', 'BBY-': '15007000',
                       # Boxing
                       'BOX-': '15014000',
                       # Motor racing
                       'CAR-': '15039000',
                       # Cycling
                       'CYC-': '15019000',
                       # American Football
                       'FBL-': '15003000', 'FBN-': '15003000', 'FBO-': '15003000',
                       # Figure skating
                       'FIG-': '15025000',
                       # Golf
                       'GLF-': '15027000',
                       # Ice Hockey
                       'HKN-': '15031000', 'HKO-': '15031000',
                       # Horse Racing
                       'RAC-': '15030000',
                       # Soccer
                       'SOC-': '15054000',
                       # Tennis
                       'TEN-': '15065000',
                       # Cricket
                       'CRI-': '15017000',
                       # Rugby league
                       'RGL-': '15048000'}

    def __init__(self):
        super().__init__()

    def can_parse(self, s_json):
        try:
            item = s_json.get('data', {}).get('item') and s_json.get('api_version')

            if item is None:
                return False

            return True
        except Exception:
            pass

        return False

    def datetime(self, string):
        try:
            return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S+0000')
        except ValueError:
            return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=utc)

    def categorisation_mapping(self, in_item, item):
        """
        Function that maps categorisation fields may be overloaded if not required
        :param in_item:
        :param item:
        :return:
        """
        if in_item.get('subject'):
            categories = [{'qcode': c.get('code')} for c in in_item.get('subject') if c.get('rels') == ['category']]
            if len(categories):
                item['anpa_category'] = [categories[0]]
                self._map_category_codes(item)

        self._map_sluglines_to_subjects(item=item)

    def _map_category_codes(self, item):
        """Map the category code that has been received to a more palatable value

        :param item:
        :return:
        """
        category_code_map = get_resource_service('vocabularies').find_one(req=None, _id='ap_category_map')
        if category_code_map:
            map = {c['ap_code']: c['category_code'] for c in category_code_map['items'] if c['is_active']}
            for category in item.get('anpa_category', []):
                category['qcode'] = map.get(category.get('qcode').lower(), map.get('default'))

    def _map_sluglines_to_subjects(self, item):
        """The first few characters of the slugline may match AP supplimetal categories this is used to set the subject code.

        :param item:
        :return:
        """
        if len(item.get('slugline', '')) > 4:
            qcode = self.slug_code_map.get(item['slugline'][:4])
            if qcode:
                try:
                    item['subject'] = []
                    item['subject'].append({'qcode': qcode, 'name': subject_codes[qcode]})
                except KeyError:
                    logger.debug("Subject code '%s' not found" % qcode)

    def parse(self, s_json, provider=None):
        in_item = s_json.get('data', {}).get('item')
        nitf_item = s_json.get('nitf', {})
        item = {'guid': in_item.get('altids', {}).get('itemid') + ':' + str(in_item.get('version'))}
        item['source'] = provider.get('source') if provider else 'AP'

        for copy_property in self.direct_copy_properties:
            if in_item.get(copy_property) is not None:
                item[copy_property] = in_item[copy_property]

        if in_item.get('versioncreated'):
            item['versioncreated'] = self.datetime(in_item.get('versioncreated'))

        if in_item.get('firstcreated'):
            item['firstcreated'] = self.datetime(in_item.get('firstcreated'))

        if len(in_item.get('infosource', [])):
            item['original_source'] = ','.join([n.get('name') for n in in_item.get('infosource', [])])

        if in_item.get('datelinelocation'):
            cities = app.locators.find_cities()
            # Try to find a single matching city either by city and country or city country and state
            located = [c for c in cities if c['city'] == in_item.get('datelinelocation').get('city') and
                       c['country'] == in_item.get('datelinelocation').get('countryname')]
            if len(located) > 1:
                located = [c for c in cities if c['city'] == in_item.get('datelinelocation').get('city') and
                           c['country'] == in_item.get('datelinelocation').get('countryname') and
                           c['state'] == in_item.get('datelinelocation').get('countryareaname')]
            if len(located) == 1:
                item['dateline'] = dict()
                item['dateline']['located'] = located[0]
                item['dateline']['source'] = provider.get('source')
                item['dateline']['text'] = format_dateline_to_locmmmddsrc(item['dateline']['located'],
                                                                          get_date(item['firstcreated']),
                                                                          provider.get('source'))

        if len(in_item.get('bylines', [])):
            item['byline'] = ','.join([n.get('name') if n.get('name') else n.get('by', '') + (
                ' ({})'.format(n.get('title')) if n.get('title') else '') for n in in_item.get('bylines', [])])
            if item.get('byline').startswith('By '):
                item['byline'] = item['byline'][3:]

        if len(in_item.get('usageterms', [])):
            item['usageterms'] = ', '.join([n for n in in_item.get('usageterms', [])])

        if in_item.get('type') == 'picture':
            if in_item.get('renditions', {}).get('main'):
                item['renditions'] = {
                    'baseImage': {'href': in_item.get('renditions', {}).get('main', {}).get('href')}}

            if in_item.get('description_caption'):
                item['description_text'] = in_item.get('description_caption')
                item['archive_description'] = in_item.get('description_caption')

            if in_item.get('description_creditline'):
                item['credit'] = in_item.get('description_creditline')

            if in_item.get('photographer', {}).get('name'):
                item['byline'] = in_item.get('photographer', {}).get('name')

        if in_item.get('type') == 'text':
            # Peel off the take key if possible
            if ',' in item['slugline']:
                item['anpa_take_key'] = item['slugline'].split(',')[1]
                item['slugline'] = item['slugline'].split(',')[0]
            if item['slugline'].startswith('BC-'):
                item['slugline'] = item['slugline'][3:]
            if item.get('ednote', '').startswith('Eds:'):
                item['ednote'] = item['ednote'][5:]
            if in_item.get('headline_extended'):
                item['abstract'] = in_item.get('headline_extended')

            self.categorisation_mapping(in_item, item)

            # Map the urgency to urgency and priority
            if in_item.get('urgency'):
                item[ITEM_URGENCY] = int(in_item['urgency']) if in_item['urgency'] <= 5 else 5
                item[ITEM_PRIORITY] = self.priority_map.get(in_item['urgency'], 5)

            if nitf_item.get('body_html'):
                # item['body_html'] = sd_etree.clean_html_str(nitf_item.get('body_html'))
                item['body_html'] = nitf_item.get('body_html').replace('<block id="Main">', '').replace('</block>', '')

        return item


register_feed_parser(APMediaFeedParser.NAME, APMediaFeedParser())
