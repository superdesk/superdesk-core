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
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, FORMAT, FORMATS
from superdesk.utc import utcnow
from datetime import datetime
from superdesk.logging import logger
import superdesk
from apps.publish.content.common import ITEM_PUBLISH
import uuid
import html


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
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
                for line in lines:
                    if self.START_OF_MESSAGE in line:
                        return True
                return False
        except Exception as ex:
            logger.exception(ex)
            return False

    def parse(self, filename, provider=None):
        try:
            item = {}
            self.set_item_defaults(item, provider)

            with open(filename, 'r', encoding='latin-1') as f:
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
                                item[FORMAT] = FORMATS.PRESERVED
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
                if item.get(FORMAT) == FORMATS.PRESERVED:
                    item['body_html'] = '<pre>' + html.escape(item['body_html']) + '</pre>'

            return self.post_process_item(item, provider)

        except Exception as ex:
            raise ParserError.ZCZCParserError(exception=ex, provider=provider)

    def set_item_defaults(self, item, provider):
        item['urgency'] = 5
        item['pubstatus'] = 'usable'
        item['versioncreated'] = utcnow()
        item[ITEM_TYPE] = CONTENT_TYPE.TEXT
        # Pagemasters
        if provider.get('source') == 'PMF':
            item[FORMAT] = FORMATS.PRESERVED
            item['original_source'] = 'Pagemasters'
            self.KEYWORD = '#'
            self.TAKEKEY = '@'
            self.HEADLINE = ':'
            self.header_map = {self.KEYWORD: self.ITEM_SLUGLINE, self.TAKEKEY: self.ITEM_TAKE_KEY,
                               self.HEADLINE: self.ITEM_HEADLINE}
        elif provider.get('source') == 'MNET':
            # Medianet
            item[FORMAT] = FORMATS.PRESERVED
            item['original_source'] = 'Medianet'
            item['urgency'] = 8
            self.HEADLINE = ':'
            self.header_map = {'%': None, self.HEADLINE: self.ITEM_HEADLINE}
        elif provider.get('source') == 'BRA':
            # Racing system
            item[FORMAT] = FORMATS.PRESERVED
        else:
            item[FORMAT] = FORMATS.HTML

    def post_process_item(self, item, provider):
        """
        Applies the transormations required based on the provider of the content and the item it's self
        :param item:
        :param provider:
        :return: item
        """
        try:
            # Pagemasters sourced content is Greyhound or Trot related, maybe AFL otherwise financial
            if provider.get('source') == 'PMF':
                # is it a horse or dog racing item
                if item.get(self.ITEM_SLUGLINE, '').find('Grey') != -1 or item.get(self.ITEM_SLUGLINE, '').find(
                        'Trot') != -1 or item.get(self.ITEM_SLUGLINE, '').find('Gallop') != -1:
                    # Don't look for the date in the TAB Dividends
                    if item.get(self.ITEM_HEADLINE, '').find('TAB DIVS') == -1:
                        try:
                            raceday = datetime.strptime(item.get(self.ITEM_HEADLINE, ''), '%d/%m/%Y')
                            item[self.ITEM_TAKE_KEY] = 'Fields ' + raceday.strftime('%A')
                        except:
                            item[self.ITEM_TAKE_KEY] = 'Fields'
                        # it's the dogs
                        if item.get(self.ITEM_SLUGLINE, '').find('Grey') != -1:
                            item[self.ITEM_HEADLINE] = item.get(self.ITEM_SLUGLINE) + 'hound ' + item.get(
                                self.ITEM_TAKE_KEY,
                                '')
                            item[self.ITEM_SUBJECT] = [{'qcode': '15082000', 'name': subject_codes['15082000']}]
                        if item.get(self.ITEM_SLUGLINE, '').find('Trot') != -1:
                            item[self.ITEM_HEADLINE] = item.get(self.ITEM_SLUGLINE) + ' ' + item.get(self.ITEM_TAKE_KEY,
                                                                                                     '')
                            item[self.ITEM_SUBJECT] = [{'qcode': '15030003', 'name': subject_codes['15030003']}]
                    else:
                        if item.get(self.ITEM_SLUGLINE, '').find('Greyhound') != -1:
                            item[self.ITEM_SUBJECT] = [{'qcode': '15082000', 'name': subject_codes['15082000']}]
                        if item.get(self.ITEM_SLUGLINE, '').find('Trot') != -1:
                            item[self.ITEM_SUBJECT] = [{'qcode': '15030003', 'name': subject_codes['15030003']}]
                        if item.get(self.ITEM_SLUGLINE, '').find('Gallop') != -1:
                            item[self.ITEM_SUBJECT] = [{'qcode': '15030001', 'name': subject_codes['15030001']}]
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
                    if lines[1] and lines[1].find(':POTTED :') != -1:
                        item[self.ITEM_SLUGLINE] = lines[1][9:]
                elif lines[1] and lines[1].find('RACING : ') != -1:
                    item[self.ITEM_HEADLINE] = lines[1][8:]
                    item[self.ITEM_SLUGLINE] = lines[1][8:]
                elif lines[0] and lines[0].find('YY FORM') != -1:
                    item[self.ITEM_HEADLINE] = lines[1]
                    item[self.ITEM_SLUGLINE] = lines[1]
                elif lines[1] and lines[1].find(':POTTED :') != -1:
                    item[self.ITEM_HEADLINE] = lines[1][9:]
                    item[self.ITEM_SLUGLINE] = lines[1][9:]
                else:
                    for line_num in range(3, min(len(lines), 6)):
                        if lines[line_num] != '':
                            item[self.ITEM_HEADLINE] = lines[line_num].strip()
                            item[self.ITEM_SLUGLINE] = lines[line_num].strip()
                            break
                # Truncate the slugline and headline to the lengths defined on the validators if required if required
                lookup = {'act': ITEM_PUBLISH, 'type': CONTENT_TYPE.TEXT}
                validators = superdesk.get_resource_service('validators').get(req=None, lookup=lookup)
                if validators.count():
                    max_slugline_len = validators[0]['schema']['slugline']['maxlength']
                    max_headline_len = validators[0]['schema']['headline']['maxlength']
                    if self.ITEM_SLUGLINE in item and len(item[self.ITEM_SLUGLINE]) > max_slugline_len:
                        # the overflow of the slugline is dumped in the take key
                        item[self.ITEM_TAKE_KEY] = item.get(self.ITEM_SLUGLINE)[max_slugline_len:]
                        item[self.ITEM_SLUGLINE] = item[self.ITEM_SLUGLINE][:max_slugline_len]
                    if self.ITEM_HEADLINE in item:
                        item[self.ITEM_HEADLINE] = item[self.ITEM_HEADLINE][:max_headline_len] \
                            if len(item[self.ITEM_HEADLINE]) > max_headline_len else item[self.ITEM_HEADLINE]
        except Exception as ex:
            logger.exception(ex)

        return item


register_feed_parser(ZCZCFeedParser.NAME, ZCZCFeedParser())
