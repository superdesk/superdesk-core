# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import arrow
import datetime
import pytz
from pytz import utc, timezone  # flake8: noqa

tzinfo = getattr(datetime, 'tzinfo', object)


def utcnow():
    """Get tz aware datetime object.

    Remove microseconds which can't be persisted by mongo so we have
    the values consistent in both mongo and elastic.
    """
    if hasattr(datetime.datetime, 'now'):
        now = datetime.datetime.now(tz=utc)
    else:
        now = datetime.datetime.utcnow()
    return now.replace(microsecond=0)


def get_date(date_or_string):
    if date_or_string:
        return arrow.get(date_or_string).datetime


def get_expiry_date(minutes, offset=None):
    if minutes is None or minutes <= 0:
        return None
    if offset:
        if type(offset) is datetime.datetime:
            try:
                return offset + datetime.timedelta(minutes=minutes)
            except OverflowError:
                return
        else:
            raise TypeError('offset must be a datetime.date, not a %s' % type(offset))
    else:
        try:
            return utcnow() + datetime.timedelta(minutes=minutes)
        except OverflowError:  # very big number, never expire
            return


def local_to_utc(local_tz_name, local_datetime):
    """
    Converts the local_datetime to utc
    :param local_tz_name: Name of the local timezone
    :param local_datetime: Value of the local datetime
    :return: the utc datetime
    """
    if local_datetime:
        local_tz = pytz.timezone(local_tz_name)
        utc_dat = local_tz.localize(local_datetime.replace(tzinfo=None))
        return pytz.utc.normalize(utc_dat)


def utc_to_local(local_tz_name, utc_datetime):
    """
    Converts utc datetime to local
    :param local_tz_name: Name of the local timezone
    :param utc_datetime: Value of the utc datetime
    :return: local datetime
    """
    if utc_datetime and local_tz_name:
        if not utc_datetime.tzinfo:
            utc_datetime = utc_datetime.replace(tzinfo=pytz.utc)
        local_tz = pytz.timezone(local_tz_name)
        local_dt = utc_datetime.astimezone(local_tz)
        return local_tz.normalize(local_dt)


def set_time(current_datetime, timestr):
    """Set time of given datetime according to timestr.

    Time format for timestr is `%H:%M:%S`, eg. 10:14:00.

    :param datetime current_datetime
    :param string timestr
    :param int second
    """
    if timestr is None:
        timestr = '00:00:00'
    time = datetime.datetime.strptime(timestr, '%H:%M:%S')
    return current_datetime.replace(hour=time.hour, minute=time.minute, second=time.second)


def get_timezone_offset(local_tz_name, utc_datetime):
    """
    Get the timezone offset
    :param string local_tz_name:
    :param datetime utc_datetime:
    :return string utc offset
    """
    try:
        local_dt = utc_to_local(local_tz_name, utc_datetime)
        return local_dt.strftime('%z')
    except Exception:
        return utcnow().strftime('%z')


def query_datetime(datetime_value, query):
    """Checks the datetime_value against the query provided.

    The query format is similar to that of MongoDB BSON comparison operators.
    It uses `$eq`, `$gt`, `$gte`, `$lt`, `$lte` and `$ne`. Combine these operators together in a dictionary
    to provide the datetime checking functionality. This is currently used when finding files from Amazon S3, but
    could possibly be used in other areas.

    :param datetime.datetime datetime_value: The datetime value used to check against the query
    :param dict query: The query parameters used to check against the datetime_value
    :return boolean: True if all comparison operators pass, else False
    """
    if '$lte' in query and datetime_value > query['$lte']:
        return False
    elif '$lt' in query and datetime_value >= query['$lt']:
        return False
    elif '$gte' in query and datetime_value < query['$gte']:
        return False
    elif '$gt' in query and datetime_value <= query['$gt']:
        return False
    elif '$eq' in query and datetime_value != query['$eq']:
        return False
    elif '$ne' in query and datetime_value == query['$ne']:
        return False
    return True
