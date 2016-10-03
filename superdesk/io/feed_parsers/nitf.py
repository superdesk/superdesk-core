# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
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
logger = logging.getLogger(__name__)

SETTINGS_MAPPING_PARAM = 'NITF_MAPPING'
SUBJECT_TYPE = 'tobject.subject.type'
SUBJECT_MATTER = 'tobject.subject.matter'
SUBJECT_DETAIL = 'tobject.subject.detail'

subject_fields = (SUBJECT_TYPE, SUBJECT_MATTER, SUBJECT_DETAIL)


class SkipValue(Exception):
    """Exception used in callback when a value is not needed"""


class NITFFeedParser(XMLFeedParser):
    """
    Feed Parser which can parse if the feed is in NITF format.
    """

    # FIXME: some behaviour here are specific to AAP (e.g. getPlace)
    #        they have been kept to avoid breaking AAP, but they can
    #        now be moved to Superdesk's settings in aap branch

    NAME = 'nitf'

    def __init__(self):
        super().__init__()
        self.default_mapping = {
            'guid': {'xpath': 'head/docdata/doc-id/@id-string',
                     'default': None
                     },
            'uri': {'xpath': 'head/docdata/doc-id/@id-string',
                    'default': None
                    },
            'urgency': {'xpath': 'head/docdata/urgency/@ed-urg',
                        'default_attr': 5,
                        'filter_value': int,
                        },
            'pubstatus': {'xpath': 'head/docdata/@management-status',
                          'default_attr': 'usable',
                          },
            'firstcreated': {'xpath': 'head/docdata/date.issue',
                             'filter': self.get_norm_datetime,
                             },
            'versioncreated': {'xpath': 'head/docdata/date.issue',
                               'filter': self.get_norm_datetime,
                               },
            'expiry': {'xpath': 'head/docdata/date.expire',
                       'filter': self.get_norm_datetime,
                       },
            'subject': self.get_subjects,
            'body_html': self.get_content,
            FORMAT: self.get_format,
            'place': self.get_place,
            'keywords': {'xpath': 'head/docdata',
                         'filter': self.get_keywords,
                         },
            'genre': self.get_genre,
            'ednote': 'head/docdata/ed-msg/@info',
            'headline': self.get_headline,
            'abstract': self.get_abstract,
            'byline': self.get_byline,
            # metadata
            'slugline': "head/meta/[@name='anpa-keyword']/@content",
            'ingest_provider_sequence': "head/meta/[@name='anpa-sequence']/@content",
            'anpa_category': {'xpath': "head/meta/[@name='anpa-category']",
                              'filter': lambda elem: [{'qcode': elem.get('content'), 'name': ''}],
                              },
            'word_count': {'xpath': "head/meta/[@name='anpa-wordcount']",
                           'filter': lambda elem: int(elem.get('content')),
                           },
            'anpa_take_key': "head/meta/[@name='anpa-keyword']",
            'priority': {'xpath': "head/meta/[@name='aap-priority']",
                         'filter': lambda elem: self.map_priority(elem.get('content')),
                         },
            'original_creator': self.get_original_creator,
            'version_creator': self.get_version_creator,
            'original_source': "head/meta/[@name='aap-source']/@content",
            'source': "head/meta/[@name='aap-source']/@content",
            'task': self.get_task,
        }
        self.metadata_mapping = None

    def _parse_xpath(self, xpath):
        """Parse xpath and handle final attribute."""
        last_idx = xpath.rfind('/')
        if last_idx == -1:
            msg = "No path separator found in xpath {}, ignoring it".format(xpath)
            logger.warn(msg)
            raise ValueError(msg)
        last = xpath[last_idx + 1:].rstrip()
        if last.startswith('@'):
            # an attribute is requested
            return {'xpath': xpath[:last_idx], 'attribute': last[1:]}
        else:
            return {'xpath': xpath}

    def _parse_mapping(self, value):
        if isinstance(value, dict):
            if not value:
                return {}
            try:
                xpath = value['xpath']
            except KeyError:
                return value
            else:
                # we parse xpath to handle final @attribute syntax
                try:
                    value.update(self._parse_xpath(xpath))
                except ValueError:
                    # xpath is invalid, we ignore the key
                    # a waring is already logged in self._parse_xpath
                    value = {}
                if 'filter' in value and 'attribute' in value:
                    logging.warn('"filter" and "attribte" should not be used in the same mapping,\
                        "attribute" will not be used: {}'.format(value))
                return value
        elif isinstance(value, str):
            if not value:
                return {}
            try:
                return self._parse_xpath(value)
            except ValueError:
                return {}
        elif callable(value):
            return {'callback': value}
        else:
            logger.warn("Can't parse mapping value {}, ignoring it".format(value))
            return {}

    def _generate_mapping(self):
        """Generate self.metadata_mapping according to available mappings.

        The following mappings are used in this order (last is more important):
            - self.default_mapping
            - self.MAPPING, intended for sublasses
            - NITF_MAPPING dictionary which can be put in settings
        If a value is a non-empty string, it is a xpath, @attribute can be used as last path component.
        If value is empty string/dict, the key will be ignored
        If value is a callable, it will be executed with nitf Element as argument, return value will be used.
        If a dictionary is used as value, following keys can be used:
            xpath: path to the element
            attribute: attribute to take in this element (if not present, content will be used)
            default: value to use if element doesn't exists (default: doesn't set the key)
            default_attr: value if element exist but attribute is missing
            filter: callable to be used with found element
            filter_value: callable to be used with found value
            key_hook: a callable which store itself the resulting value in the item,
                      usefull for specific behaviours when several values goes to same key
                      callable will get item and value as arguments.
            update: a bool which indicate that default mapping must be updated instead of overwritten
        Note the difference between using a callable directly, and "filter" in a dict:
        the former get the root element and can be skipped with SkipValue, while the
        later get an element found with xpath.
        """
        try:
            class_mapping = self.MAPPING
        except AttributeError:
            class_mapping = {}

        settings_mapping = getattr(superdesk.config, SETTINGS_MAPPING_PARAM)
        if settings_mapping is None:
            logging.info("No mapping found in settings for NITF parser, using default one")
            settings_mapping = {}

        mapping = self.metadata_mapping = {}

        for source_mapping in (self.default_mapping, class_mapping, settings_mapping):
            for key, value in source_mapping.items():
                key_mapping = self._parse_mapping(value)
                if key_mapping.get('update', False) and key in mapping:
                    mapping[key].update(key_mapping)
                else:
                    mapping[key] = key_mapping

    def can_parse(self, xml):
        return xml.tag == 'nitf'

    def parse(self, xml, provider=None):
        if self.metadata_mapping is None:
            self._generate_mapping()
        item = {ITEM_TYPE: CONTENT_TYPE.TEXT,  # set the default type.
                }
        try:
            for key, mapping in self.metadata_mapping.items():
                if not mapping:
                    # key is ignored
                    continue
                try:
                    xpath = mapping['xpath']
                except KeyError:
                    # no xpath, we must have a callable
                    try:
                        value = mapping['callback'](xml)
                    except KeyError:
                        logging.warn("invalid mapping for key {}, ignoring it".format(key))
                        continue
                    except SkipValue:
                        continue
                else:
                    elem = xml.find(xpath)
                    if elem is None:
                        try:
                            value = mapping['default']
                        except KeyError:
                            # if there is not default value we skip the key
                            continue
                    else:
                        # we have an element,
                        # do we want a filter, an attribute or the content?
                        try:
                            # filter
                            value = mapping['filter'](elem)
                        except KeyError:
                            try:
                                attribute = mapping['attribute']
                            except KeyError:
                                # content
                                value = ''.join(elem.itertext())
                            else:
                                # attribute
                                value = elem.get(attribute, mapping.get('default_attr'))

                try:
                    # filter_value is applied on found value
                    value = mapping['filter_value'](value)
                except KeyError:
                    pass

                if 'key_hook' in mapping:
                    mapping['key_hook'](item, value)
                else:
                    item[key] = value

            elem = xml.find('body/body.head/dateline/location/city')
            if elem is not None:
                self.set_dateline(item, city=elem.text)

            item.setdefault('word_count', get_word_count(item['body_html']))
            return item
        except Exception as ex:
            raise ParserError.nitfParserError(ex, provider)

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

    def get_subjects(self, tree):
        """Finds all the subject tags in the passed tree and returns the parsed subjects.

        All entries will have both the name and qcode populated.

        :param tree:
        :return: a list of subject dictionaries
        """
        subjects = []
        qcodes = []  # we check qcodes to avoid duplicates
        for elem in tree.findall('head/tobject/tobject.subject'):
            qcode = elem.get('tobject.subject.refnum')
            if qcode in qcodes:
                # we ignore duplicates
                continue
            else:
                qcodes.append(qcode)
            for field in subject_fields:
                if elem.get(field):
                    if field == SUBJECT_TYPE:
                        field_qcode = qcode[:2] + '000000'
                    elif field == SUBJECT_MATTER:
                        field_qcode = qcode[:5] + '000'
                    else:
                        field_qcode = qcode

                    if subject_codes.get(field_qcode) and \
                            not any(c['qcode'] == field_qcode for c in subjects):
                        subjects.append({
                            'name': elem.get(field),
                            'qcode': field_qcode
                        })

            # if the subject_fields are not specified.
            if not any(c['qcode'] == qcode for c in subjects) and subject_codes.get(qcode):
                subjects.append({'name': subject_codes[qcode], 'qcode': qcode})
        return subjects

    def get_anpa_format(self, xml):
        elem = xml.find("head/meta[@name='anpa-format']")
        if elem is not None:
            content = elem.get('content')
            return content.lower() if content is not None else 'x'

    def parse_to_preformatted(self, element):
        """Extract the content of the element as a plain string with line enders

        :param element:
        :return:
        """
        elements = []
        soup = BeautifulSoup(element, 'html.parser')
        for elem in soup.findAll(True):
            elements.append(elem.get_text() + '\r\n')
        return ''.join(elements)

    def get_content(self, xml):
        elements = []
        for elem in xml.find('body/body.content'):
            elements.append(etree.tostring(elem, encoding='unicode'))
        content = ''.join(elements)
        if self.get_anpa_format(xml) == 't':
            if not content.startswith('<pre>'):
                # convert content to text in a pre tag
                content = '<pre>{}</pre>'.format(self.parse_to_preformatted(content))
            else:
                content = self.parse_to_preformatted(content)
        return content

    def get_format(self, xml):
        anpa_format = self.get_anpa_format(xml)
        if anpa_format is not None:
            return FORMATS.PRESERVED if anpa_format == 't' else FORMATS.HTML

        body_elem = xml.find('body/body.content')
        # if the body contains only a single pre tag we mark the format as preserved
        if len(body_elem) == 1 and body_elem[0].tag == 'pre':
            return FORMATS.PRESERVED
        else:
            return FORMATS.HTML

    def get_place(self, tree):
        elem = tree.find("head/meta/[@name='aap-place']")
        if elem is None:
            return self.get_places(tree.find('head/docdata'))
        locator_map = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='locators')
        return [x for x in locator_map.get('items', []) if x['qcode'] == elem.get('content')]

    def get_places(self, docdata):
        places = []
        evloc = docdata.find('evloc')
        if evloc is not None:
            places.append({
                'name': evloc.attrib.get('city'),
                'code': evloc.attrib.get('iso-cc'),
            })
        return places

    def get_keywords(self, docdata):
        return [keyword.attrib['key'] for keyword in docdata.findall('key-list/keyword')]

    def get_genre(self, tree):
        elem = tree.find('head/tobject/tobject.property')
        if elem is None:
            raise SkipValue()
        genre = elem.get('tobject.property.type')
        genre_map = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='genre')
        if genre_map is not None:
            return [x for x in genre_map.get('items', []) if x['name'] == genre]
        else:
            raise SkipValue()

    def get_headline(self, xml):
        if xml.find('body/body.head/hedline/hl1') is not None:
            return xml.find('body/body.head/hedline/hl1').text
        else:
            if xml.find('head/title') is not None:
                return xml.find('head/title').text
        raise SkipValue()

    def get_abstract(self, xml):
        elem = xml.find('body/body.head/abstract/p')
        if elem is None:
            elem = xml.find('body/body.head/abstract')
        return elem.text if elem is not None else ''

    def get_byline(self, tree):
        elem = tree.find('body/body.head/byline')
        byline = ''
        if elem is not None:
            byline = elem.text
            person = elem.find('person')
            if person is not None:
                byline = "{} {}".format(byline.strip(), person.text.strip())
        return byline

    def get_original_creator(self, tree):
        elem = tree.find("head/meta/[@name='aap-original-creator']")
        if elem is not None:
            query = {'username': re.compile('^{}$'.format(elem.get('content')), re.IGNORECASE)}
            user = superdesk.get_resource_service('users').find_one(req=None, **query)
            if user is not None:
                return user.get('_id')
        raise SkipValue()

    def get_version_creator(self, tree):
        elem = tree.find("head/meta/[@name='aap-version-creator']")
        if elem is not None:
            query = {'username': re.compile('^{}$'.format(elem.get('content')), re.IGNORECASE)}
            user = superdesk.get_resource_service('users').find_one(req=None, **query)
            if user:
                return user.get('_id')
        raise SkipValue()

    def get_task(self, tree):
        desk_name = tree.find('head/meta[@name="aap-desk"]')
        if desk_name is not None:
            desk = superdesk.get_resource_service('desks').find_one(req=None, name=desk_name.get('content'))
            if desk:
                task = {'desk': desk.get('_id')}
                stage_name = tree.find('head/meta[@name="aap-stage"]')
                if stage_name is not None:
                    lookup = {'$and': [{'name': stage_name.get('content')}, {'desk': str(desk.get('_id'))}]}
                    stages = superdesk.get_resource_service('stages').get(req=None, lookup=lookup)
                    if stages is not None and stages.count() == 1:
                        task['stage'] = stages[0].get('_id')
                return task
        raise SkipValue()


register_feed_parser(NITFFeedParser.NAME, NITFFeedParser())
