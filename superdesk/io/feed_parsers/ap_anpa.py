# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .anpa import ANPAFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.io.iptc import subject_codes
from flask import current_app as app
from apps.archive.common import format_dateline_to_locmmmddsrc
from superdesk.utc import get_date
from superdesk import get_resource_service
from superdesk.etree import parse_html
import logging
import re

logger = logging.getLogger("AP_ANPAFeedParser")


class AP_ANPAFeedParser(ANPAFeedParser):
    """
    Feed parser for AP supplied ANPA, maps category codes and maps the prefix on some sluglines to subject codes
    """

    NAME = 'ap_anpa1312'

    label = 'AP ANPA Parser'

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

    def parse(self, file_path, provider=None):
        item = super().parse(file_path, provider)
        self.ap_derive_dateline(item)
        self.map_category_codes(item)
        self.map_sluglines_to_subjects(item)
        if 'headline' not in item:
            self._fix_headline(item)
        return item

    def map_category_codes(self, item):
        """Map the category code that has been received to a more palatable value

        :param item:
        :return:
        """
        category_code_map = get_resource_service('vocabularies').find_one(req=None, _id='ap_category_map')
        if category_code_map:
            map = {c['ap_code']: c['category_code'] for c in category_code_map['items'] if c['is_active']}
            for category in item.get('anpa_category', []):
                category['qcode'] = map.get(category.get('qcode').lower(), map.get('default'))

    def map_sluglines_to_subjects(self, item):
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

    def ap_derive_dateline(self, item):
        """This function looks for a dateline in the article body an uses that.

        :param item:
        :return: item populated with a dateline
        """
        try:
            html = item.get('body_html')
            if html:
                parsed = parse_html(html, content='html')
                for par in parsed.xpath('/div/child::*'):
                    if not par.text:
                        continue
                    city, source, the_rest = par.text.partition(' (AP) _ ')
                    if source:
                        # sometimes the city is followed by a comma and either a date or a state
                        city = city.split(',')[0]
                        if any(char.isdigit() for char in city):
                            return
                        cities = app.locators.find_cities()
                        located = [c for c in cities if c['city'].lower() == city.lower()]
                        item.setdefault('dateline', {})
                        item['dateline']['located'] = located[0] if len(located) == 1 else {'city_code': city,
                                                                                            'city': city,
                                                                                            'tz': 'UTC',
                                                                                            'dateline': 'city'}
                        item['dateline']['source'] = item.get('original_source', 'AP')
                        item['dateline']['text'] = format_dateline_to_locmmmddsrc(item['dateline']['located'],
                                                                                  get_date(item['firstcreated']),
                                                                                  source=item.get('original_source',
                                                                                                  'AP'))
                        break

            return item
        except Exception:
            logging.exception('AP dateline extraction exception')

    def _parse_ednote(self, header_lines, item):
        """
        Attempt to parse the ednote, If no ednote is found by the base class try another pattern
        :param header_lines:
        :param item:
        :return:
        """
        super()._parse_ednote(header_lines, item)
        if not item.get('ednote'):
            for line in header_lines:
                m = re.search("(\(?)Eds: (.*)(\)?)", line)
                if m:
                    item['ednote'] = m.group(0).strip()[:-1].replace('Eds: ', '')
                    break

    def _fix_headline(self, item):
        """
        AP Alerts do not get a healdine parsed out so pick up the first par of the content and put it in the headline
        :param item:
        :return:
        """
        try:
            html = item.get('body_html')
            if html:
                parsed = parse_html(html, content='html')
                pars = parsed.xpath('/div/child::*')
                if pars and len(pars) > 0:
                    city, source, the_rest = pars[0].text.partition(' (AP) _ ')
                    if the_rest:
                        item['headline'] = the_rest
                    else:
                        item['headline'] = pars[0].text
        except Exception:
            pass


register_feed_parser(AP_ANPAFeedParser.NAME, AP_ANPAFeedParser())
