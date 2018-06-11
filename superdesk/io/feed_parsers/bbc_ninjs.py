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
import json
from copy import deepcopy

from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import FeedParser
from superdesk.io.iptc import subject_codes
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_TAG
from superdesk.metadata.utils import generate_guid

logger = logging.getLogger(__name__)


class BBCNINJSFeedParser(FeedParser):
    """
    Feed Parser for the BBC's NINJS variant
    """

    # Variant documentation can be found at https://docs.ldrs.org.uk/

    NAME = 'bbc_ninjs'

    label = 'BBC NINJS Variant Parser'

    direct_copy_properties = ('uri', 'language', 'headline', 'urgency', 'pubstatus',
                              'mimetype', 'body_text', 'body_html', 'byline',
                              'description_text')

    # A dictionary of known subjects and their nearest IPTC qcode analogs
    subject_trans = {'policing': '02003000', 'fire-and-rescue-services': '11006001', 'crime': '02001000',
                     'transport': '04015000', 'education': '05000000', 'planning-permission': '11016007',
                     'highways': '04015003', 'waste-management': '04005007', 'public-safety': '11006002',
                     'social-care': '07011000', 'trading-standards': '04008015', 'libraries': '01009000',
                     'rubbish-collection': '04005007', 'recycling': '06009000', 'council-tax': '11013000',
                     'environmental-health': '06005000', 'leisure': '10010000', 'litter': '06005000',
                     'revenue-collection': '04008019', 'health': '07000000', 'dog-fouling': '06000000',
                     'housing': '11016002', 'graffiti': '06000000', 'fly-posting': '06000000',
                     'social-services': '14025004'}

    def __init__(self):
        super().__init__()

    def can_parse(self, s_json):
        try:
            item_ident = re.search('\"total\": *[0-9]+', s_json).group()

            if item_ident is None:
                return False

            results_str = re.search('[0-9]+', item_ident).group()

            return results_str is not None and int(results_str) > 0
        except Exception:
            pass

        return False

    def parse(self, s_json, provider=None):
        parsed = []
        json_items = json.loads(s_json).get('item', [])

        for json_item in json_items:
            parsed.extend(self._parse_item(json_item))

        return parsed

    def _parse_item(self, item):
        items = []

        main = self._parse_main(item)
        items.append(main)

        subjects = main.setdefault('subject', [])
        for subject in item['subject']:
            try:
                parsed_subject = self._parse_subject(subject)
                if parsed_subject is not None:
                    subjects.append(parsed_subject)
            except Exception as ex:
                logger.exception("Exception parsing subject, {}".format(ex))

        associations = main.setdefault('associations', {})
        for association in item['associations']:
            try:
                key, parsed_association = self._parse_association(association)
                associations[key] = parsed_association

                # Also create an image item out of the association rendition
                image = self._create_image(association, main)
                items.append(image)
            except Exception as ex:
                logger.exception("Exception parsing association, {}".format(ex))

        # If there's only a single type we don't need to build a composite type
        if len(items) > 1:
            items.append(self._create_package(items, main))

        return items

    def _create_package(self, items, main):
        """Builds a composite package for the entire article
        :param items:
        :param main: The main article body
        :return: A composite item dict
        """
        package = {
            ITEM_TYPE: CONTENT_TYPE.COMPOSITE,
            'guid': main['guid'] + '-package',
            'versioncreated': main['versioncreated'],
            'firstcreated': main['firstcreated'],
            'headline': main['headline'],
            'groups': [
                {
                    'id': 'root',
                    'role': 'grpRole:NEP',
                    'refs': [{'idRef': 'main'}],
                }, {
                    'id': 'main',
                    'role': 'main',
                    'refs': [],
                }
            ]
        }

        item_references = package['groups'][1]['refs']
        item_references.append({'residRef': main['guid']})

        for item in items:
            if item != main:
                item_references.append({'residRef': item['guid']})

        return package

    def _create_image(self, association, main):
        """Builds an image item from an association
        :param association: The raw association in BBC's ninjs variant
        :param main: The main article body
        :return: A image item dict
        """
        url = association['renditions']['original']['href']
        guid_hash = hashlib.sha1(url.encode('utf8')).hexdigest()

        item = {
            'guid': generate_guid(type=GUID_TAG, id=guid_hash + '-image'),
            ITEM_TYPE: CONTENT_TYPE.PICTURE,
            'versioncreated': main['versioncreated'],
            'firstcreated': main['firstcreated'],
            'headline': association.get('headline', ''),
            'description_text': association.get('description_text', ''),
            'renditions': {
                'baseImage': {
                    'href': url
                }
            }
        }

        return item

    def _parse_association(self, association):
        """Parses a BBC ninjs association
        :param association:
        :return: association dict
        """
        key = association.pop('id')
        # BBC don't use 'featuremedia', they typically use 'featureimage'
        if re.match('^feature', key):
            key = 'featuremedia'

        parsed = deepcopy(association)

        parsed[ITEM_TYPE] = CONTENT_TYPE.PICTURE
        url = association['renditions']['original']['href']
        guid_hash = hashlib.sha1(url.encode('utf8')).hexdigest()
        parsed['guid'] = generate_guid(type=GUID_TAG, id=guid_hash)

        return key, parsed

    def _parse_subject(self, subject):
        """Parses a BBC ninjs subject
        :param subject:
        :return: subject dict
        """
        parsed = {}
        if (subject['lang'] != 'en') or (subject['rel'] != 'category'):
            return

        search_subject = re.sub('^category:', '', subject['code'])

        # Check if we can find the IPTC subject from the custom BBC ones
        if search_subject in self.subject_trans:
            qcode = self.subject_trans[search_subject]
            parsed['qcode'] = qcode
            parsed['name'] = subject_codes[qcode]
            return parsed

        logger.warn("Could not find subject code ({})".format(subject))

    def _parse_main(self, json):
        """Parses the main body of text and metadata
        :param json:
        :return: dict of article metadata and body
        """
        # No GUID is included so generate one from the link
        main = {}

        guid_hash = hashlib.sha1(json['uri'].encode('utf8')).hexdigest()
        main['guid'] = generate_guid(type=GUID_TAG, id=guid_hash)
        # Copy over all attributes which are the same as Superdesk's ninjs variant
        for copy_property in self.direct_copy_properties:
            if json.get(copy_property) is not None:
                main[copy_property] = json[copy_property]

        main['versioncreated'] = self._parse_date(json['versioncreated'])
        main['firstcreated'] = self._parse_date(json['firstcreated'])

        if json.get('embargotime'):
            main['embargo'] = json['embargotime']

        main['type'] = self._convert_type(json['type'])
        return main

    def _parse_date(self, string):
        """Attempts to parse BBC ninjs time in format YYYY-MM-DDTHH:MM:SS
        :param string:
        :return: datetime
        """
        return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S')

    def _convert_type(self, content_type):
        """Attempts to convert BBC's types to standard ninjs types
        :param content_type:
        :return:
        """
        if content_type == 'image':
            return CONTENT_TYPE.PICTURE
        if content_type == 'story' or content_type == 'advisory':
            return CONTENT_TYPE.TEXT

        logger.error("could not find content type ({}), defaulting to text".format(content_type))

        return CONTENT_TYPE.TEXT


register_feed_parser(BBCNINJSFeedParser.NAME, BBCNINJSFeedParser())
