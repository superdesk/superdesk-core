# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE
from superdesk.errors import ParserError
from superdesk import etree as sd_etree
import superdesk
import dateutil.parser
import logging
from pytz import timezone

logger = logging.getLogger(__name__)
NS = {'r': 'http://tempuri.org/',
      'a': 'http://schemas.microsoft.com/2003/10/Serialization/Arrays'}


class RitzauFeedParser(XMLFeedParser):
    """
    Feed Parser which can parse Ritzau XML feed
    """

    _subjects_map = None

    NAME = 'ritzau'
    label = "Ritzau feed"

    def __init__(self):
        super().__init__()

        self.default_mapping = {
            'id': '//NewsID/text()',
            'guid': '//NewsID/text()',
            'body_html': {'xpath': '//content/text()',
                          'filter': sd_etree.clean_html_str},
            'firstcreated': {'xpath': '//PublishDate/text()',
                             'filter': self._publish_date_filter,
                             },
            'versioncreated': {'xpath': '//PublishDate/text()',
                               'filter': self._publish_date_filter,
                               },
            'headline': '//headline/text()',
            'priority': '//Priority/text()',
            'keywords': {'xpath': '//strapline/text()',
                         'filter': lambda v: list(filter(None, v.split('/')))},
            'abstract': '//subtitle',
            'byline': '//origin',
            'place': '//town',
            'version': {'xpath': '//version/text()',
                        'filter': int},
            'ednote': '//Tilredaktionen/text()',
            'subject': {'xpath': '//IPTCList/a:int/text()',
                        'list': True,
                        'filter': self._subject_filter}}

    @property
    def subjects_map(self):
        if self._subjects_map is None:
            voc_subjects = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='subject_custom')
            if voc_subjects is not None:
                self._subjects_map = {i['qcode']: i for i in voc_subjects['items']}
            else:
                self._subjects_map = {}
        return self._subjects_map

    def can_parse(self, xml):
        return xml.tag.endswith('RBNews')

    def parse(self, xml, provider=None):
        item = {ITEM_TYPE: CONTENT_TYPE.TEXT,  # set the default type.
                }
        try:
            self.do_mapping(item, xml, namespaces=NS)
        except Exception as ex:
            raise ParserError.parseMessageError(ex, provider)
        return item

    def get_datetime(self, value):
        return dateutil.parser.parse(value)

    def _subject_filter(self, qcode):
        self.subjects_map
        try:
            subject = self.subjects_map[qcode]
        except KeyError:
            return None
        else:
            if not subject.get('is_active', False):
                return None
            name = subject.get('name', '')

        return {'qcode': qcode, 'name': name, 'scheme': 'subject_custom'}

    def _publish_date_filter(self, date_string):
        dt = dateutil.parser.parse(date_string)
        return dt.replace(tzinfo=timezone('CET'))


register_feed_parser(RitzauFeedParser.NAME, RitzauFeedParser())
