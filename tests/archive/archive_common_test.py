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
from datetime import timedelta

from apps.archive.common import is_genre, BROADCAST_GENRE, get_utc_schedule
from superdesk.utc import utcnow


class ArchiveCommonTestCase(unittest.TestCase):
    def test_broadcast_content(self):
        content = {"genre": [{"name": "Broadcast Script", "qcode": "Broadcast Script"}]}

        self.assertTrue(is_genre(content, BROADCAST_GENRE))

    def test_broadcast_content_if_genre_is_none(self):
        content = {"genre": None}

        self.assertFalse(is_genre(content, BROADCAST_GENRE))

    def test_broadcast_content_if_genre_is_empty_list(self):
        content = {"genre": []}

        self.assertFalse(is_genre(content, BROADCAST_GENRE))

    def test_broadcast_content_if_genre_is_other_than_broadcast(self):
        content = {"genre": [{"name": "Article", "qcode": "Article"}]}

        self.assertFalse(is_genre(content, BROADCAST_GENRE))
        self.assertTrue(is_genre(content, "Article"))

    def test_get_utc_schedule(self):
        embargo_date = utcnow() + timedelta(minutes=10)
        content = {"embargo": embargo_date}
        utc_schedule = get_utc_schedule(content, "embargo")
        self.assertEqual(utc_schedule, embargo_date)
