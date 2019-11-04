# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import logging
import datetime

from copy import deepcopy
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import FeedParser
from superdesk.utc import utc
from superdesk.metadata.utils import generate_tag_from_url

logger = logging.getLogger(__name__)


class NINJSFeedParser(FeedParser):
    """
    Feed Parser for NINJS format
    """

    NAME = 'ninjs'

    label = 'NINJS Feed Parser'

    direct_copy_properties = ('usageterms', 'language', 'headline', 'copyrightnotice',
                              'urgency', 'pubstatus', 'mimetype', 'copyrightholder', 'ednote',
                              'body_text', 'body_html', 'slugline', 'keywords',
                              'extra', 'byline', 'description_text', 'profile')

    items = []

    def __init__(self):
        super().__init__()

    def can_parse(self, file_path):
        try:
            with open(file_path, 'r') as f:
                ninjs = json.load(f)
                if ninjs.get('uri') or ninjs.get('guid'):
                    return True
        except Exception:
            pass
        return False

    def parse(self, file_path, provider=None):
        self.items = []
        with open(file_path, 'r') as f:
            ninjs = json.load(f)

        self.items.append(self._transform_from_ninjs(ninjs))
        return self.items

    def _transform_from_ninjs(self, ninjs):
        guid = ninjs.get('guid')
        if not guid and ninjs.get('uri'):
            guid = generate_tag_from_url(ninjs['uri'], 'urn')
        item = {'guid': guid,
                'type': ninjs.get('type'),
                'uri': ninjs.get('uri')}

        for copy_property in self.direct_copy_properties:
            if ninjs.get(copy_property) is not None:
                item[copy_property] = ninjs[copy_property]

        if ninjs.get('source'):
            item['original_source'] = ninjs['source']

        if ninjs.get('priority'):
            item['priority'] = int(ninjs['priority'])
        else:
            ninjs['priority'] = 5

        if ninjs.get('genre'):
            item['genre'] = self._format_qcodes(ninjs['genre'])

        if ninjs.get('service'):
            item['anpa_category'] = self._format_qcodes(ninjs['service'])

        if ninjs.get('subject'):
            item['subject'] = self._format_qcodes(ninjs['subject'])

        if ninjs.get('versioncreated'):
            item['versioncreated'] = self.datetime(ninjs.get('versioncreated'))

        if ninjs.get('firstcreated'):
            item['firstcreated'] = self.datetime(ninjs.get('firstcreated'))

        if ninjs.get('associations'):
            item['associations'] = {}

        for key, associated_item in ninjs.get('associations', {}).items():
            if associated_item:
                self.items.append(self._transform_from_ninjs(associated_item))
                if associated_item.get('type') == 'picture' and associated_item.get('body_text'):
                    associated_item['alt_text'] = associated_item.get('body_text')
                if associated_item.get('versioncreated'):
                    associated_item['versioncreated'] = self.datetime(associated_item['versioncreated'])
                item['associations'][key] = deepcopy(associated_item)

        if ninjs.get('renditions', {}).get('baseImage'):
            item['renditions'] = {'baseImage': {'href': ninjs.get('renditions', {}).get('original', {}).get('href')}}

        if ninjs.get('located'):
            item['dateline'] = {'located': {'city': ninjs.get('located')}}

        if ninjs.get('type') == 'picture' and ninjs.get('body_text'):
            item['alt_text'] = ninjs.get('body_text')

        if ninjs.get('type') == 'text' and ninjs.get('description_text'):
            item['abstract'] = ninjs.get('description_text')

        if ninjs.get('place'):
            item['place'] = self._format_qcodes(ninjs['place'])

        if ninjs.get('authors'):
            item['authors'] = self._parse_authors(ninjs['authors'])

        if not item.get('body_html') and ninjs.get('body_xhtml'):
            item['body_html'] = ninjs['body_xhtml']

        return item

    def _format_qcodes(self, items):
        subjects = []
        for item in items:
            subject = {'name': item.get('name'), 'qcode': item.get('code')}
            if item.get('scheme'):
                subject['scheme'] = item.get('scheme')
            subjects.append(subject)

        return subjects

    def datetime(self, string):
        try:
            return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S+0000').replace(tzinfo=utc)
        except ValueError:
            return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=utc)

    def _parse_authors(self, authors):
        return [self._parse_author(author) for author in authors]

    def _parse_author(self, author):
        parsed = {
            'name': author['name'],
            'role': author.get('role', ''),
        }

        if author.get('avatar_url'):
            parsed['avatar_url'] = author['avatar_url']

        if author.get('biography'):
            parsed['biography'] = author['biography']

        return parsed


register_feed_parser(NINJSFeedParser.NAME, NINJSFeedParser())
