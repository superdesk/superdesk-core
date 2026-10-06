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
import logging
import pytz

from typing import Optional
from pytz import utc, timezone

tzinfo = getattr(datetime, "tzinfo", object)
EXPIRY_OVERFLOW_DAYS = 99999
logger = logging.getLogger(__name__)


def utcnow():
    """Get tz aware datetime object.

    Remove microseconds which can't be persisted by mongo so we have
    the values consistent in both mongo and elastic.
    """
    if hasattr(datetime.datetime, "now"):
        now = datetime.datetime.now(tz=utc)
    else:
        now = datetime.datetime.utcnow()
    return now.replace(microsecond=0)


def get_date(date_or_string) -> Optional[datetime.datetime]:
    if date_or_string:
        return arrow.get(date_or_string).datetime
    return None


def get_expiry_date(minutes, offset=None) -> Optional[datetime.datetime]:
    if minutes is None or minutes <= 0:
        return None
    if offset and type(offset) is not datetime.datetime:
        raise TypeError("offset must be a datetime.date, not a %s" % type(offset))
    base = offset or utcnow()
    try:
        return base + datetime.timedelta(minutes=minutes)
    except OverflowError:
        logger.warning("Expiry duration overflow; using %s days from %s", EXPIRY_OVERFLOW_DAYS, base)
        try:
            return base + datetime.timedelta(days=EXPIRY_OVERFLOW_DAYS)
        except OverflowError:
            return datetime.datetime.max.replace(tzinfo=base.tzinfo)


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


def utc_to_local(local_tz_name, utc_datetime) -> datetime.datetime:
    """
    Converts utc datetime to local
    :param local_tz_name: Name of the local timezone
    :param utc_datetime: Value of the utc datetime
    :return: local datetime
    """
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
        timestr = "00:00:00"
    time = datetime.datetime.strptime(timestr, "%H:%M:%S")
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
        return local_dt.strftime("%z")
    except Exception:
        return utcnow().strftime("%z")


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
    if "$lte" in query and datetime_value > query["$lte"]:
        return False
    elif "$lt" in query and datetime_value >= query["$lt"]:
        return False
    elif "$gte" in query and datetime_value < query["$gte"]:
        return False
    elif "$gt" in query and datetime_value <= query["$gt"]:
        return False
    elif "$eq" in query and datetime_value != query["$eq"]:
        return False
    elif "$ne" in query and datetime_value == query["$ne"]:
        return False
    return True
