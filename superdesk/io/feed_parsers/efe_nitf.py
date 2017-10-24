#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.nitf import NITFFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.metadata.item import FORMAT
from superdesk.io.iptc import subject_codes
from flask import current_app as app
from apps.archive.common import format_dateline_to_locmmmddsrc
from superdesk.utc import get_date
import logging

logger = logging.getLogger("EFEFeedParser")


class EFEFeedParser(NITFFeedParser):
    """
    Feed parser for the NITF feed from Agencia EFE
    """

    NAME = 'efe_nitf'

    label = 'EFE NITF'

    def __init__(self):
        self.MAPPING = {
            'guid': {'xpath': 'head/docdata/doc-id/@id-string',
                     'default': None
                     },
            'uri': {'xpath': 'head/docdata/doc-id/@id-string',
                    'default': None
                    },
            'urgency': {'xpath': 'head/docdata/urgency/@ed-urg',
                        'default_attr': 5,
                        'filter': int,
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
            'slugline': {'xpath': 'head/docdata',
                         'filter': self.get_slugline,
                         },
            'genre': self.get_genre,
            'ednote': 'head/docdata/ed-msg/@info',
            'headline': self.get_headline,
            'abstract': self.get_abstract,
        }

        super().__init__()
        self.default_mapping = {}

    def parse(self, xml, provider=None):
        item = super().parse(xml, provider)
        self.derive_dateline(item)
        return item

    def derive_dateline(self, item):
        """
        Attempt to derive a dateline using the place, only if there is exactly one match on the city can we be sure we
        have the correct country.
        :param item:
        :return:
        """
        try:
            if len(item.get('place', [])) == 1:
                cities = app.locators.find_cities()
                city = item.get('place', '')[0].get('name', '')
                located = [c for c in cities if c['city'].lower() == city.lower()]
                if len(located) == 1:
                    item.setdefault('dateline', {})
                    item['dateline']['located'] = located[0]
                    item['dateline']['source'] = item.get('original_source', 'EFE')
                    item['dateline']['text'] = format_dateline_to_locmmmddsrc(item['dateline']['located'],
                                                                              get_date(item['firstcreated']),
                                                                              source=item.get('original_source',
                                                                                              'EFE'))
                item.pop('place')
        except Exception:
            logging.exception('EFE dateline extraction exception')

    def get_slugline(self, docdata):
        """
        Get the keywords and put the first one into the slugline
        :param docdata:
        :return:
        """
        keywords = self.get_keywords(docdata)
        return keywords[0] if len(keywords) > 0 else None

    def get_subjects(self, tree):
        """Finds all the IPTC subject tags in the passed tree and returns the parsed subjects.

        All entries will have both the name and qcode populated.

        :param tree:
        :return: a list of subject dictionaries
        """
        subjects = []
        qcodes = []  # we check qcodes to avoid duplicates
        for elem in tree.findall('head/tobject/tobject.subject[@tobject.subject.ipr="IPTC"]'):
            qcode = elem.get('tobject.subject.refnum')
            if qcode in qcodes:
                # we ignore duplicates
                continue
            else:
                qcodes.append(qcode)

            # if the subject_fields are not specified.
            if not any(c['qcode'] == qcode for c in subjects) and subject_codes.get(qcode):
                subjects.append({'name': subject_codes[qcode], 'qcode': qcode})
        return subjects


register_feed_parser(EFEFeedParser.NAME, EFEFeedParser())
