# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.newsml_1_2 import NewsMLOneFeedParser
from superdesk.io import register_feed_parser
from superdesk.utc import utcnow
from pytz import utc


class AFPNewsMLOneFeedParser(NewsMLOneFeedParser):
    """AFP specific NewsML parser.

    Feed Parser which can parse the AFP feed basicaly it is in NewsML 1.2 format,
    but the firstcreated and versioncreated times are localised.
    """

    NAME = 'afpnewsml12'

    def parse(self, xml, provider=None):
        item = super().parse(xml, provider)
        item['firstcreated'] = utc.localize(item['firstcreated']) if item.get('firstcreated') else utcnow()
        item['versioncreated'] = utc.localize(item['versioncreated']) if item.get('versioncreated') else utcnow()
        return item


register_feed_parser(AFPNewsMLOneFeedParser.NAME, AFPNewsMLOneFeedParser())
