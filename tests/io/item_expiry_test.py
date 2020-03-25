# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime, timedelta

from superdesk.tests import TestCase
from superdesk.io.commands.update_ingest import is_not_expired


class ItemExpiryTestCase(TestCase):

    def test_expiry_no_dateinfo(self):
        self.assertTrue(is_not_expired({}, None))

    def test_expiry_overflow(self):
        item = {'versioncreated': datetime.now()}
        delta = timedelta(minutes=999999999999)
        self.assertTrue(is_not_expired(item, delta))
