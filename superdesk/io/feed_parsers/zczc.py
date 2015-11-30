# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license*.
from superdesk.io import register_feed_parser
from superdesk.io.feed_parsers import FileFeedParser
from superdesk.errors import ParserError
from superdesk.io.iptc import subject_codes
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE
from superdesk.utc import utcnow
from datetime import datetime
import uuid


class ZCZCFeedParser(FileFeedParser):
    """
    Feed Parser which can parse if the feed is in ZCZC format.

    It is expected that the stories contained in the files will be framed by the strings
    ZCZC

    NNNN

    * the NNNN is optional
    """

    NAME = 'zczc'

    START_OF_MESSAGE = 'ZCZC'
    END_OF_MESSAGE = 'NNNN'

    CATEGORY = '$'
    KEYWORD = ':'
    TAKEKEY = '='
    HEADLINE = '^'
    FORMAT = '*'  # *format "X" text "T" tabular
    SERVICELEVEL = '&'  # &service level - Default A but for results should match category
    IPTC = '+'  # +IPTC Subject Reference Number as defined in the SubjectReference.ini file

    # Possible values for format
    TEXT = 'X'
    TABULAR = 'T'

    ITEM_SLUGLINE = 'slugline'
    ITEM_HEADLINE = 'headline'
    ITEM_ANPA_CATEGORY = 'anpa_category'
    ITEM_SUBJECT = 'subject'
    ITEM_TAKE_KEY = 'anpa_take_key'

    header_map = {KEYWORD: ITEM_SLUGLINE, TAKEKEY: ITEM_TAKE_KEY,
                  HEADLINE: ITEM_HEADLINE, SERVICELEVEL: None}

    def can_parse(self, file_path):
        try:
            with open(file_path, 'r', encoding='ascii') as f:
                return self.START_OF_MESSAGE in f.readlines()[0]
        finally:
            return False

    def parse(self, filename, provider=None):
        try:
            item = {}
            self.set_item_defaults(item, provider)

            with open(filename, 'r', encoding='ascii') as f:
                lines = f.readlines()
                header = False
                body = False
                for line in lines:
                    if self.START_OF_MESSAGE in line and not header:
                        item['guid'] = filename + str(uuid.uuid4())
                        header = True
                        continue
                    if header:
                        if line[0] in self.header_map:
                            if self.header_map[line[0]]:
                                item[self.header_map[line[0]]] = line[1:-1]
                            continue
                        if line[0] == self.CATEGORY:
                            item[self.ITEM_ANPA_CATEGORY] = [{'qcode': line[1]}]
                            continue
                        if line[0] == self.FORMAT:
                            if line[1] == self.TEXT:
                                item[ITEM_TYPE] = CONTENT_TYPE.TEXT
                                continue
                            if line[1] == self.TABULAR:
                                item[ITEM_TYPE] = CONTENT_TYPE.PREFORMATTED
                                continue
                            continue
                        if line[0] == self.IPTC:
                            iptc_code = line[1:-1]
                            item[self.ITEM_SUBJECT] = [{'qcode': iptc_code, 'name': subject_codes[iptc_code]}]
                            continue
                        header = False
                        body = True
                        item['body_html'] = line
                    else:
                        if self.END_OF_MESSAGE in line:
                            break
                        if body:
                            item['body_html'] = item.get('body_html', '') + line
            return self.post_process_item(item, provider)

        except Exception as ex:
            raise ParserError.ZCZCParserError(exception=ex, provider=provider)

    def set_item_defaults(self, item, provider):
        item['urgency'] = 5
        item['pubstatus'] = 'usable'
        item['versioncreated'] = utcnow()
        # Pagemasters
        if provider.get('source') == 'PMF':
            item[ITEM_TYPE] = CONTENT_TYPE.PREFORMATTED
            item['original_source'] = 'Pagemasters'
            self.KEYWORD = '#'
            self.TAKEKEY = '@'
            self.HEADLINE = ':'
            self.header_map = {self.KEYWORD: self.ITEM_SLUGLINE, self.TAKEKEY: self.ITEM_TAKE_KEY,
                               self.HEADLINE: self.ITEM_HEADLINE}
        elif provider.get('source') == 'MNET':
            # Medianet
            item[ITEM_TYPE] = CONTENT_TYPE.PREFORMATTED
            item['original_source'] = 'Medianet'
            item['urgency'] = 8
            self.HEADLINE = ':'
            self.header_map = {'%': None, self.HEADLINE: self.ITEM_HEADLINE}
        elif provider.get('source') == 'BRA':
            # Racing system
            item[ITEM_TYPE] = CONTENT_TYPE.PREFORMATTED
        else:
            item[ITEM_TYPE] = CONTENT_TYPE.TEXT

    def post_process_item(self, item, provider):
        """
        Applies the transormations required based on the provider of the content and the item it's self
        :param item:
        :param provider:
        :return: item
        """
        # Pagemasters sourced content is Greyhound or Trot related, maybe AFL otherwise financial
        if provider.get('source') == 'PMF':
            # is it a horse or dog racing item
            if item.get(self.ITEM_SLUGLINE, '').find('Grey') != -1 or item.get(self.ITEM_SLUGLINE, '').find(
                    'Trot') != -1:
                raceday = datetime.strptime(item.get(self.ITEM_HEADLINE, ''), '%d/%m/%Y')
                item[self.ITEM_TAKE_KEY] = 'Fields ' + raceday.strftime('%A')
                if item.get(self.ITEM_SLUGLINE, '').find('Grey') != -1:
                    item[self.ITEM_HEADLINE] = item.get(self.ITEM_SLUGLINE) + 'hound ' + item.get(self.ITEM_TAKE_KEY,
                                                                                                  '')
                    item[self.ITEM_SUBJECT] = [{'qcode': '15082002', 'name': subject_codes['15082002']}]
                if item.get(self.ITEM_SLUGLINE, '').find('Trot') != -1:
                    item[self.ITEM_HEADLINE] = item.get(self.ITEM_SLUGLINE) + ' ' + item.get(self.ITEM_TAKE_KEY, '')
                    item[self.ITEM_SUBJECT] = [{'qcode': '15030000', 'name': subject_codes['15030000']}]
                item[self.ITEM_ANPA_CATEGORY] = [{'qcode': 'r'}]
            elif item.get(self.ITEM_SLUGLINE, '').find('AFL') != -1:
                item[self.ITEM_ANPA_CATEGORY] = [{'qcode': 't'}]
                item[self.ITEM_SUBJECT] = [{'qcode': '15084000', 'name': subject_codes['15084000']}]
            else:
                item[self.ITEM_ANPA_CATEGORY] = [{'qcode': 'f'}]
                item[self.ITEM_SUBJECT] = [{'qcode': '04000000', 'name': subject_codes['04000000']}]
        elif provider.get('source') == 'BRA':
            # It is from the Racing system
            item[self.ITEM_ANPA_CATEGORY] = [{'qcode': 'r'}]
            item[self.ITEM_SUBJECT] = [{'qcode': '15030001', 'name': subject_codes['15030001']}]
            lines = item['body_html'].split('\n')
            if lines[2] and lines[2].find(':SPORT -') != -1:
                item[self.ITEM_HEADLINE] = lines[2][9:]
            elif lines[1] and lines[1].find('RACING : ') != -1:
                item[self.ITEM_HEADLINE] = lines[1][8:]
            elif lines[0] and lines[0].find('YY FORM') != -1:
                item[self.ITEM_HEADLINE] = lines[1]
            elif lines[1] and lines[1].find(':POTTED :') != -1:
                item[self.ITEM_HEADLINE] = lines[1][9:]
            else:
                item[self.ITEM_HEADLINE] = lines[2]

        return item


register_feed_parser(ZCZCFeedParser.NAME, ZCZCFeedParser())
