# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import unittest
from superdesk.activity import ActivityService


class ActivityTestCase(unittest.TestCase):

    def test_if_user_is_in_recipients(self):
        activity = {'recipients': [{'user_id': '1', 'read': True},
                                   {'user_id': '2', 'read': False}]}

        self.assertTrue(ActivityService().is_recipient(activity, '1'))
        self.assertTrue(ActivityService().is_recipient(activity, '2'))
        self.assertFalse(ActivityService().is_recipient(activity, '3'))

    def test_is_read(self):
        activity = {'recipients': [{'user_id': '1', 'read': True},
                                   {'user_id': '2', 'read': False}]}

        self.assertTrue(ActivityService().is_read(activity, '1'))
        self.assertFalse(ActivityService().is_read(activity, '2'))
        self.assertFalse(ActivityService().is_read(activity, '3'))
