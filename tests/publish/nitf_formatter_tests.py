# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from superdesk.publish.formatters.nitf_formatter import NITFFormatter
from superdesk.publish.formatters import Formatter
from superdesk.publish import init_app


class NitfFormatterTest(TestCase):
    def setUp(self):
        super().setUp()
        self.formatter = NITFFormatter()
        self.base_formatter = Formatter()
        init_app(self.app)

    def test_append_legal(self):
        article = {
            'slugline': 'Obama Republican Healthc',
            'flags': {'marked_for_legal': True}
        }

        slugline = self.base_formatter.append_legal(article)
        self.assertEqual(slugline, 'Legal: Obama Republican Healthc')
        slugline = self.base_formatter.append_legal(article, truncate=True)
        self.assertEqual(slugline, 'Legal: Obama Republican ')

    def test_append_legal_when_not_legal(self):
        article = {
            'slugline': 'Obama Republican Healthc',
            'flags': {'marked_for_legal': False}
        }

        slugline = self.base_formatter.append_legal(article)
        self.assertEqual(slugline, 'Obama Republican Healthc')
