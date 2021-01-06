# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import pytz
import unittest
from datetime import datetime, timedelta
from superdesk.utc import (
    get_date,
    utcnow,
    get_expiry_date,
    local_to_utc,
    utc_to_local,
    get_timezone_offset,
    query_datetime,
)
from pytz import utc, timezone  # flake8: noqa
from nose.tools import assert_raises


class UTCTestCase(unittest.TestCase):
    def test_get_date(self):
        self.assertIsInstance(get_date("2012-12-12"), datetime)
        self.assertIsInstance(get_date(datetime.now()), datetime)
        self.assertIsNone(get_date(None))

    def test_utcnow(self):
        self.assertIsInstance(utcnow(), datetime)
        date1 = get_date(datetime.now(tz=utc))
        date2 = utcnow()
        self.assertEqual(date1.year, date2.year)
        self.assertEqual(date1.month, date2.month)
        self.assertEqual(date1.day, date2.day)
        self.assertEqual(date1.hour, date2.hour)
        self.assertEqual(date1.minute, date2.minute)
        self.assertEqual(date1.second, date2.second)

    def test_get_expiry_date(self):
        self.assertIsInstance(get_expiry_date(minutes=60), datetime)
        date1 = utcnow() + timedelta(minutes=60)
        date2 = get_expiry_date(minutes=60)
        self.assertEqual(date1.year, date2.year)
        self.assertEqual(date1.month, date2.month)
        self.assertEqual(date1.day, date2.day)
        self.assertEqual(date1.hour, date2.hour)
        self.assertEqual(date1.minute, date2.minute)
        self.assertEqual(date1.second, date2.second)

    def test_get_expiry_date_none(self):
        self.assertIsNone(get_expiry_date(0))
        self.assertIsNone(get_expiry_date(None))

    def test_get_expiry_date_with_offset(self):
        offset = utcnow() + timedelta(minutes=10)
        date1 = offset + timedelta(minutes=5)
        date2 = get_expiry_date(minutes=5, offset=offset)
        self.assertEqual(date1.year, date2.year)
        self.assertEqual(date1.month, date2.month)
        self.assertEqual(date1.day, date2.day)
        self.assertEqual(date1.hour, date2.hour)
        self.assertEqual(date1.minute, date2.minute)
        self.assertEqual(date1.second, date2.second)

    def test_get_expiry_date_bad_offset_raises_error(self):
        with assert_raises(TypeError) as error_context:
            offset = "01.02.2013 13:30"
            get_expiry_date(minutes=5, offset=offset)

    def test_get_expiry_date_overflow(self):
        self.assertIsNone(get_expiry_date(9999999999999))
        self.assertIsNone(get_expiry_date(9999999999999, utcnow()))

    def test_utc_to_local(self):
        # with day light saving on
        utc_dt = datetime(2015, 2, 8, 23, 0, 0, 0, pytz.UTC)
        local_dt = utc_to_local("Australia/Sydney", utc_dt)
        self.assertEqual(utc_dt.hour - local_dt.hour, 13)

        # without day light saving
        utc_dt = datetime(2015, 6, 8, 23, 0, 0, 0, pytz.UTC)
        local_dt = utc_to_local("Australia/Sydney", utc_dt)
        self.assertEqual(utc_dt.hour - local_dt.hour, 14)

    def test_local_to_utc(self):
        # with day light saving on
        local_tz = pytz.timezone("Australia/Sydney")
        local_dt = datetime(2015, 2, 8, 18, 0, 0, 0, local_tz)
        utc_dt = local_to_utc("Australia/Sydney", local_dt)
        self.assertEqual(local_dt.hour - utc_dt.hour, 11)

        # without day light saving
        local_dt = local_tz.normalize(datetime(2015, 6, 8, 18, 0, 0, 0).replace(tzinfo=local_tz))
        utc_dt = local_to_utc("Australia/Sydney", local_dt)
        self.assertEqual(local_dt.hour - utc_dt.hour, 10)

    def test_local_to_utc_europe(self):
        utc_dt = local_to_utc("Europe/Prague", datetime(2016, 4, 19, 15, 8, 0))
        self.assertEqual("2016-04-19T13:08:00+00:00", utc_dt.isoformat())

    def test_get_timezone_offset_sydney(self):
        utc_dt = datetime(2015, 2, 8, 23, 0, 0, 0, pytz.UTC)
        offset = get_timezone_offset("Australia/Sydney", utc_dt)
        self.assertEqual(offset, "+1100")

        utc_dt = datetime(2015, 9, 8, 23, 0, 0, 0, pytz.UTC)
        offset = get_timezone_offset("Australia/Sydney", utc_dt)
        self.assertEqual(offset, "+1000")

    def test_get_timezone_offset_prague(self):
        utc_dt = datetime(2015, 2, 8, 23, 0, 0, 0, pytz.UTC)
        offset = get_timezone_offset("Europe/Prague", utc_dt)
        self.assertEqual(offset, "+0100")

        utc_dt = datetime(2015, 9, 8, 23, 0, 0, 0, pytz.UTC)
        offset = get_timezone_offset("Europe/Prague", utc_dt)
        self.assertEqual(offset, "+0200")

    def test_get_timezone_offset_wrong_input(self):
        utc_dt = "test"
        offset = get_timezone_offset("Europe/Prague", utc_dt)
        self.assertEqual(offset, "+0000")

        utc_dt = datetime(2015, 9, 8, 23, 0, 0, 0, pytz.UTC)
        offset = get_timezone_offset("Europe/Sydney", utc_dt)
        self.assertEqual(offset, "+0000")


class UTCQueryTest(unittest.TestCase):
    def setUp(self):
        self.now = utcnow()
        self.past = self.now - timedelta(hours=1)
        self.future = self.now + timedelta(hours=1)

    def test_lte(self):
        self.assertTrue(query_datetime(self.past, {"$lte": self.now}))
        self.assertTrue(query_datetime(self.now, {"$lte": self.now}))
        self.assertFalse(query_datetime(self.future, {"$lte": self.now}))

    def test_lt(self):
        self.assertTrue(query_datetime(self.past, {"$lt": self.now}))
        self.assertFalse(query_datetime(self.now, {"$lt": self.now}))
        self.assertFalse(query_datetime(self.future, {"$lt": self.now}))

    def test_gte(self):
        self.assertFalse(query_datetime(self.past, {"$gte": self.now}))
        self.assertTrue(query_datetime(self.now, {"$gte": self.now}))
        self.assertTrue(query_datetime(self.future, {"$gte": self.now}))

    def test_gt(self):
        self.assertFalse(query_datetime(self.past, {"$gt": self.now}))
        self.assertFalse(query_datetime(self.now, {"$gt": self.now}))
        self.assertTrue(query_datetime(self.future, {"$gt": self.now}))

    def test_eq(self):
        self.assertFalse(query_datetime(self.past, {"$eq": self.now}))
        self.assertTrue(query_datetime(self.now, {"$eq": self.now}))
        self.assertFalse(query_datetime(self.future, {"$eq": self.now}))

    def test_neq(self):
        self.assertTrue(query_datetime(self.past, {"$ne": self.now}))
        self.assertFalse(query_datetime(self.now, {"$ne": self.now}))
        self.assertTrue(query_datetime(self.future, {"$ne": self.now}))

    def test_combination(self):
        self.assertTrue(query_datetime(self.now, {"$lt": self.future, "$gt": self.past}))
        self.assertFalse(query_datetime(self.past, {"$lt": self.future, "$gt": self.now}))
