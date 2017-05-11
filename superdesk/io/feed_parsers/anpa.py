# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import re

from datetime import datetime

from superdesk.errors import ParserError
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import FileFeedParser
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, Priority, GUID_FIELD, GUID_TAG, FORMAT, FORMATS
from superdesk.utc import utc
from superdesk.metadata.utils import generate_guid


class ANPAFeedParser(FileFeedParser):
    """
    Feed Parser which can parse if the feed is in ANPA 1312 format.
    """

    NAME = 'anpa1312'

    def can_parse(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                lines = [line for line in f]
                return re.match(b'\x16\x16\x01([a-z])([0-9]{4})\x1f([a-z0-9-]+)', lines[0], flags=re.I)
        except:
            return False

    def parse(self, file_path, provider=None):
        try:
            item = {ITEM_TYPE: CONTENT_TYPE.TEXT, GUID_FIELD: generate_guid(type=GUID_TAG), FORMAT: FORMATS.HTML}

            with open(file_path, 'rb') as f:
                lines = [line for line in f]

            # parse first header line
            m = re.match(b'\x16\x16\x01([a-z])([0-9]{4})\x1f([a-z-]+)', lines[0], flags=re.I)
            if m:
                item['provider_sequence'] = m.group(2).decode()

            # parse second header line
            m = re.match(
                b'([a-z]) ([a-z])(\x13|\x14)(\x11|\x12) (am-|pm-|bc-|ap-)([a-z-.]+)(.*) '
                b'([0-9]{1,2})-([0-9]{1,2}) ([0-9]{4})',
                lines[1], flags=re.I)
            if m:
                item['priority'] = self.map_priority(m.group(1).decode())
                item['anpa_category'] = [{'qcode': m.group(2).decode()}]
                item['slugline'] = m.group(6).decode('latin-1', 'replace')
                item['anpa_take_key'] = m.group(7).decode('latin-1', 'replace').strip()
                item['word_count'] = int(m.group(10).decode())
                if m.group(4) == b'\x12':
                    item[FORMAT] = FORMATS.PRESERVED

            # parse created date at the end of file
            m = re.search(b'\x03([a-z]+)-([a-z]+)-([0-9]+-[0-9]+-[0-9]+ [0-9]{2}[0-9]{2})GMT', lines[-4], flags=re.I)
            if m:
                item['firstcreated'] = datetime.strptime(m.group(3).decode(), '%m-%d-%y %H%M').replace(tzinfo=utc)
                item['versioncreated'] = item['firstcreated']

            # parse anpa content
            body = b''.join(lines[2:])
            m = re.match(b'\x02(.*)\x03', body, flags=re.M + re.S)
            if m:
                text = m.group(1).decode('latin-1', 'replace').split('\n')

                if item.get(FORMAT) == FORMATS.PRESERVED:
                    # ANPA defines a number of special characters e.g. TLI (Tab Line Inicator) Hex x08 and
                    # TTS Space Band Hex x10 These will be replaced, there will likely be others
                    body_lines = [l.strip('^').replace('\b', '%08').replace('\x10', '%10') for l in text if
                                  l.startswith(('\t', '^', '\b'))]
                    item['body_html'] = '<pre>' + '\n'.join(body_lines) + '</pre>'
                else:
                    body_lines = [l.strip() for l in text if l.startswith(('\t'))]
                    item['body_html'] = '<p>' + '</p><p>'.join(body_lines) + '</p>'

                # content metadata
                header_lines = [l.strip('^<= ') for l in text if l.startswith('^')]
                if len(header_lines) > 1:
                    item['headline'] = header_lines[1].rstrip('\r\n^<= ')
                if len(header_lines) > 3:
                    item['byline'] = header_lines[-2].rstrip('\r\n^<= ')

                    # if there is no body use header lines
                    if len(body_lines) == 1 and not body_lines[0]:
                        item['body_html'] = '<p>' + '</p><p>'.join(header_lines[2:]) + '</p>'

                # slugline
                if len(header_lines) > 1:
                    m = re.match('[A-Z]{2}-[A-Z]{2}--([a-z-0-9.]+)', header_lines[0], flags=re.I)
                    if m:
                        item['slugline'] = m.group(1)

                # ednote
                self._parse_ednote(header_lines, item)

            return item
        except Exception as ex:
            raise ParserError.anpaParseFileError(file_path, ex)

    def _parse_ednote(self, header_lines, item):
        for line in header_lines:
            m = re.search("EDITOR'S NOTE _(.*)", line)
            if m:
                item['ednote'] = m.group(1).strip()

    def map_priority(self, source_priority):
        mapping = {
            'f': Priority.Flash.value,
            'u': Priority.Urgent.value,
            'b': Priority.Three_Paragraph.value,
            'z': Priority.Ordinary.value
        }

        source_priority = source_priority.lower().strip() if isinstance(source_priority, str) else ''
        return mapping.get(source_priority, Priority.Ordinary.value)


register_feed_parser(ANPAFeedParser.NAME, ANPAFeedParser())
