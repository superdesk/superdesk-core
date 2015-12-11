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
import dateutil.parser
from superdesk.io import register_feed_parser
from superdesk.io.feed_parsers import XMLFeedParser
import xml.etree.ElementTree as etree
from superdesk.errors import ParserError
from superdesk.utc import utc
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE
from superdesk.etree import get_word_count
from superdesk.io.iptc import subject_codes

SUBJECT_TYPE = 'tobject.subject.type'
SUBJECT_MATTER = 'tobject.subject.matter'
SUBJECT_DETAIL = 'tobject.subject.detail'

subject_fields = (SUBJECT_TYPE, SUBJECT_MATTER, SUBJECT_DETAIL)


def get_places(docdata):
    places = []
    evloc = docdata.find('evloc')
    if evloc is not None:
        places.append({
            'name': evloc.attrib.get('city'),
            'code': evloc.attrib.get('iso-cc'),
        })
    return places


def get_subjects(tree):
    """
    Finds all the subject tags in the passed tree and returns the parsed subjects. All entries will have both the
    name and qcode populated.
    :param tree:
    :return: a list of subject dictionaries
    """
    subjects = []
    for elem in tree.findall('head/tobject/tobject.subject'):
        qcode = elem.get('tobject.subject.refnum')
        for field in subject_fields:
            if elem.get(field):
                if field == SUBJECT_TYPE:
                    field_qcode = qcode[:2] + '000000'
                elif field == SUBJECT_MATTER:
                    field_qcode = qcode[:5] + '000'
                else:
                    field_qcode = qcode

                if subject_codes.get(field_qcode):
                    subjects.append({
                        'name': elem.get(field),
                        'qcode': field_qcode
                    })
        if not any(c['qcode'] == qcode for c in subjects) and subject_codes.get(qcode):
            subjects.append({'name': subject_codes[qcode], 'qcode': qcode})
    return subjects


def get_keywords(docdata):
    return [keyword.attrib['key'] for keyword in docdata.findall('key-list/keyword')]


def get_content(tree):
    elements = []
    for elem in tree.find('body/body.content'):
        elements.append(etree.tostring(elem, encoding='unicode'))
    return ''.join(elements)


def get_norm_datetime(tree):
    if tree is None:
        return

    try:
        value = datetime.strptime(tree.attrib['norm'], '%Y%m%dT%H%M%S')
    except ValueError:
        try:
            value = datetime.strptime(tree.attrib['norm'], '%Y%m%dT%H%M%S%z')
        except ValueError:
            value = dateutil.parser.parse(tree.attrib['norm'])

    return utc.normalize(value) if value.tzinfo else value


def get_byline(tree):
    elem = tree.find('body/body.head/byline')
    byline = ''
    if elem is not None:
        byline = elem.text
        person = elem.find('person')
        if person is not None:
            byline = "{} {}".format(byline.strip(), person.text.strip())
    return byline


def parse_meta(tree, item):
    for elem in tree.findall('head/meta'):
        attribute_name = elem.get('name')

        if attribute_name == 'anpa-keyword':
            item['slugline'] = elem.get('content')
        elif attribute_name == 'anpa-sequence':
            item['ingest_provider_sequence'] = elem.get('content')
        elif attribute_name == 'anpa-category':
            item['anpa_category'] = [{'qcode': elem.get('content'), 'name': ''}]
        elif attribute_name == 'anpa-wordcount':
            item['word_count'] = int(elem.get('content'))
        elif attribute_name == 'anpa-takekey':
            item['anpa_take_key'] = elem.get('content')
        elif attribute_name == 'anpa-format':
            anpa_format = elem.get('content').lower() if elem.get('content') is not None else 'x'
            item[ITEM_TYPE] = CONTENT_TYPE.TEXT if anpa_format == 'x' else CONTENT_TYPE.PREFORMATTED


class NITFFeedParser(XMLFeedParser):
    """
    Feed Parser which can parse if the feed is in NITF format.
    """

    NAME = 'nitf'

    def can_parse(self, xml):
        return xml.tag == 'nitf'

    def parse(self, xml, provider=None):
        item = {}
        try:
            docdata = xml.find('head/docdata')
            # set the default type.
            item[ITEM_TYPE] = CONTENT_TYPE.TEXT
            item['guid'] = item['uri'] = docdata.find('doc-id').get('id-string')
            if docdata.find('urgency') is not None:
                item['urgency'] = int(docdata.find('urgency').get('ed-urg', '5'))
            item['pubstatus'] = (docdata.attrib.get('management-status', 'usable')).lower()
            item['firstcreated'] = get_norm_datetime(docdata.find('date.issue'))
            item['versioncreated'] = get_norm_datetime(docdata.find('date.issue'))

            if docdata.find('date.expire') is not None:
                item['expiry'] = get_norm_datetime(docdata.find('date.expire'))
            item['subject'] = get_subjects(xml)
            item['body_html'] = get_content(xml)
            item['place'] = get_places(docdata)
            item['keywords'] = get_keywords(docdata)

            if docdata.find('ed-msg') is not None:
                item['ednote'] = docdata.find('ed-msg').attrib.get('info')

            if xml.find('body/body.head/hedline/hl1') is not None:
                item['headline'] = xml.find('body/body.head/hedline/hl1').text
            else:
                if xml.find('head/title') is not None:
                    item['headline'] = xml.find('head/title').text

            elem = xml.find('body/body.head/abstract')
            item['abstract'] = elem.text if elem is not None else ''

            elem = xml.find('body/body.head/dateline/location/city')
            if elem is not None:
                self.set_dateline(item, city=elem.text)

            item['byline'] = get_byline(xml)

            parse_meta(xml, item)
            item.setdefault('word_count', get_word_count(item['body_html']))
            return item
        except Exception as ex:
            raise ParserError.nitfParserError(ex, provider)


register_feed_parser(NITFFeedParser.NAME, NITFFeedParser())
