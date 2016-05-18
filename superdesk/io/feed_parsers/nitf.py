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
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, FORMAT, FORMATS
from superdesk.etree import get_word_count
from superdesk.io.iptc import subject_codes
from bs4 import BeautifulSoup
import re
import superdesk

SUBJECT_TYPE = 'tobject.subject.type'
SUBJECT_MATTER = 'tobject.subject.matter'
SUBJECT_DETAIL = 'tobject.subject.detail'

subject_fields = (SUBJECT_TYPE, SUBJECT_MATTER, SUBJECT_DETAIL)


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
            item['firstcreated'] = self.get_norm_datetime(docdata.find('date.issue'))
            item['versioncreated'] = self.get_norm_datetime(docdata.find('date.issue'))

            if docdata.find('date.expire') is not None:
                item['expiry'] = self.get_norm_datetime(docdata.find('date.expire'))
            item['subject'] = self.get_subjects(xml)
            item['body_html'] = self.get_content(xml)
            body_elem = xml.find('body/body.content')
            # if the body contains only a single pre tag we mark the format as preserved
            if len(body_elem) == 1 and body_elem[0].tag == 'pre':
                item[FORMAT] = FORMATS.PRESERVED
            else:
                item[FORMAT] = FORMATS.HTML
            item['place'] = self.get_places(docdata)
            item['keywords'] = self.get_keywords(docdata)

            if xml.find('head/tobject/tobject.property') is not None:
                genre = xml.find('head/tobject/tobject.property').get('tobject.property.type')
                genre_map = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='genre')
                if genre_map is not None:
                    item['genre'] = [x for x in genre_map.get('items', []) if x['name'] == genre]

            if docdata.find('ed-msg') is not None:
                item['ednote'] = docdata.find('ed-msg').attrib.get('info')

            if xml.find('body/body.head/hedline/hl1') is not None:
                item['headline'] = xml.find('body/body.head/hedline/hl1').text
            else:
                if xml.find('head/title') is not None:
                    item['headline'] = xml.find('head/title').text

            elem = xml.find('body/body.head/abstract/p')
            item['abstract'] = elem.text if elem is not None else ''
            if elem is None:
                elem = xml.find('body/body.head/abstract')
                item['abstract'] = elem.text if elem is not None else ''

            elem = xml.find('body/body.head/dateline/location/city')
            if elem is not None:
                self.set_dateline(item, city=elem.text)

            item['byline'] = self.get_byline(xml)

            self.parse_meta(xml, item)
            item.setdefault('word_count', get_word_count(item['body_html']))
            return item
        except Exception as ex:
            raise ParserError.nitfParserError(ex, provider)

    def parse_to_preformatted(self, element):
        """
        Extract the contnt of the element as a plain string with line enders
        :param element:
        :return:
        """
        elements = []
        soup = BeautifulSoup(element, 'html.parser')
        for elem in soup.findAll(True):
            elements.append(elem.get_text() + '\r\n')
        return ''.join(elements)

    def parse_meta(self, tree, item):
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
                if anpa_format == 't':
                    item[FORMAT] = FORMATS.PRESERVED
                    if not item['body_html'].startswith('<pre>'):
                        # convert content to text in a pre tag
                        item['body_html'] = '<pre>' + self.parse_to_preformatted(self.get_content(tree)) + '</pre>'
                    else:
                        item['body_html'] = self.parse_to_preformatted(self.get_content(tree))
                else:
                    item[FORMAT] = FORMATS.HTML

            elif attribute_name == 'aap-priority':
                item['priority'] = self.map_priority(elem.get('content'))
            elif attribute_name == 'aap-original-creator':
                query = {'username': re.compile('^{}$'.format(elem.get('content')), re.IGNORECASE)}
                user = superdesk.get_resource_service('users').find_one(req=None, **query)
                if user is not None:
                    item['original_creator'] = user.get('_id')
            elif attribute_name == 'aap-version-creator':
                query = {'username': re.compile('^{}$'.format(elem.get('content')), re.IGNORECASE)}
                user = superdesk.get_resource_service('users').find_one(req=None, **query)
                if user:
                    item['version_creator'] = user.get('_id')
            elif attribute_name == 'aap-source':
                item['original_source'] = elem.get('content')
                item['source'] = elem.get('content')
            elif attribute_name == 'aap-original-source':
                pass
            elif attribute_name == 'aap-place':
                locator_map = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='locators')
                item['place'] = [x for x in locator_map.get('items', []) if x['qcode'] == elem.get('content')]

        desk_name = tree.find('head/meta[@name="aap-desk"]')
        if desk_name is not None:
            desk = superdesk.get_resource_service('desks').find_one(req=None, name=desk_name.get('content'))
            if desk:
                item['task'] = {'desk': desk.get('_id')}
                stage_name = tree.find('head/meta[@name="aap-stage"]')
                if stage_name is not None:
                    lookup = {'$and': [{'name': stage_name.get('content')}, {'desk': str(desk.get('_id'))}]}
                    stages = superdesk.get_resource_service('stages').get(req=None, lookup=lookup)
                    if stages is not None and stages.count() == 1:
                        item['task']['stage'] = stages[0].get('_id')

    def get_places(self, docdata):
        places = []
        evloc = docdata.find('evloc')
        if evloc is not None:
            places.append({
                'name': evloc.attrib.get('city'),
                'code': evloc.attrib.get('iso-cc'),
            })
        return places

    def get_subjects(self, tree):
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

    def get_keywords(self, docdata):
        return [keyword.attrib['key'] for keyword in docdata.findall('key-list/keyword')]

    def get_content(self, tree):
        elements = []
        for elem in tree.find('body/body.content'):
            elements.append(etree.tostring(elem, encoding='unicode'))
        return ''.join(elements)

    def get_norm_datetime(self, tree):
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

    def get_byline(self, tree):
        elem = tree.find('body/body.head/byline')
        byline = ''
        if elem is not None:
            byline = elem.text
            person = elem.find('person')
            if person is not None:
                byline = "{} {}".format(byline.strip(), person.text.strip())
        return byline


register_feed_parser(NITFFeedParser.NAME, NITFFeedParser())
