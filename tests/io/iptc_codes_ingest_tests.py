# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from copy import deepcopy

from superdesk.tests import TestCase
from superdesk.io.commands.update_ingest import process_iptc_codes


class IPTCCodesTestCase(TestCase):

    def test_unknown_iptc(self):
        """Test if an unknown IPTC code is not causing a crash"""
        item = {
            "guid": "urn:newsml:localhost:2019-02-07T12:00:00.030513:369c16e0-d6b7-40e1-8838-9c5f6a61626c",
            "subject": [{"name": "system", "qcode": "99009000"}],
        }
        # item should not be modified
        expected = deepcopy(item)

        with self.app.app_context():
            process_iptc_codes(item, {})
        self.assertEqual(item, expected)
