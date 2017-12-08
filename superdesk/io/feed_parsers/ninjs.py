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
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import FeedParser
import datetime
from superdesk.utc import utc
import json
from copy import deepcopy

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
                              'source', 'extra', 'byline', 'description_text')

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
        item = {'guid': ninjs.get('guid'),
                'type': ninjs.get('type')}

        for copy_property in self.direct_copy_properties:
            if ninjs.get(copy_property) is not None:
                item[copy_property] = ninjs[copy_property]

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

        if ninjs.get('associations', {}).get('featuremedia'):
            child_ninjs = ninjs.get('associations', {}).get('featuremedia')
            if child_ninjs:
                self.items.append(self._transform_from_ninjs(child_ninjs))
                if child_ninjs.get('type') == 'picture' and child_ninjs.get('body_text'):
                    child_ninjs['alt_text'] = child_ninjs.get('body_text')
            item['associations'] = deepcopy(ninjs.get('associations'))

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

        return item

    def _format_qcodes(self, items):
        return [{'name': item.get('name'), 'qcode': item.get('code')} for item in items]

    def datetime(self, string):
        try:
            return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S+0000')
        except ValueError:
            return datetime.datetime.strptime(string, '%Y:%m:%dT%H:%M:%SZ').replace(tzinfo=utc)


register_feed_parser(NINJSFeedParser.NAME, NINJSFeedParser())
