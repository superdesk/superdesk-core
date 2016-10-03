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
from superdesk.io import register_feed_parser
from superdesk.io.iptc import subject_codes
from flask import current_app as app
from apps.archive.common import format_dateline_to_locmmmddsrc
from superdesk.utc import get_date
from bs4 import BeautifulSoup
from superdesk import get_resource_service
import logging

logger = logging.getLogger("AP_ANPAFeedParser")


class AP_ANPAFeedParser(ANPAFeedParser):
    """
    Feed parser for AP supplied ANPA, maps category codes and maps the prefix on some sluglines to subject codes
    """

    NAME = 'ap_anpa1312'

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
        return item

    def map_category_codes(self, item):
        """Map the category code that has been received to a more palatable value

        :param item:
        :return:
        """
        for category in item.get('anpa_category', []):
            if category.get('qcode').lower() in ('a', 'p', 'w', 'n'):
                category['qcode'] = 'i'
            elif category.get('qcode').lower() == 'r':
                category['qcode'] = 'v'
            elif category.get('qcode').lower() == 'z':
                category['qcode'] = 's'
            else:
                # check if the category is defined in the system
                category_map = get_resource_service('vocabularies').find_one(req=None, _id='categories')
                if category_map:
                    if not next((code for code in category_map['items'] if
                                 code['qcode'].lower() == category['qcode'].lower() and code['is_active']), None):
                        category['qcode'] = 'i'
                else:
                    category['qcode'] = 'i'

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
                soup = BeautifulSoup(html, "html.parser")
                pars = soup.findAll('p')
                for par in pars:
                    city, source, the_rest = par.get_text().partition(' (AP) _ ')
                    if source:
                        # sometimes the city is followed by a comma and either a date or a state
                        city = city.split(',')[0]
                        if any(char.isdigit() for char in city):
                            return
                        cities = app.locators.find_cities()
                        located = [c for c in cities if c['city'].lower() == city.lower()]
                        item.setdefault('dateline', {})
                        item['dateline']['located'] = located[0] if len(located) > 0 else {'city_code': city,
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
        except:
            logging.exception('AP dateline extraction exception')


register_feed_parser(AP_ANPAFeedParser.NAME, AP_ANPAFeedParser())
