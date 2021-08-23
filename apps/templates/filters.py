# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from superdesk.utc import get_date, timezone
from superdesk import config
from superdesk.etree import parse_html
from lxml import etree

logger = logging.getLogger(__name__)


def format_datetime_filter(date_or_string, timezone_string=None, date_format=None):
    """Convert date or string to another timezone

    :param str date_or_string:
    :param str timezone_string:
    :param str date_format:
    :return str: returns string representation of the date format
    """
    try:
        date_time = get_date(date_or_string)

        timezone_string = timezone_string if timezone_string else config.DEFAULT_TIMEZONE
        tz = timezone(timezone_string)
        if tz:
            date_time = date_time.astimezone(tz)

        if date_format:
            return date_time.strftime(date_format)
        else:
            return str(date_time)

    except Exception:
        logger.warning(
            "Failed to convert datetime. Arguments: Date - {} Timezone - {} format - {}.".format(
                date_or_string, timezone_string, date_format
            )
        )
        return ""


def first_paragraph_filter(input_string):
    try:
        elem = parse_html(input_string, content="html")
    except ValueError as e:
        logger.warning(e)
    else:
        # all non-empty paragraphs: ignores <p><br></p> sections
        for p in elem.iterfind(".//p"):
            if p.text:
                return etree.tostring(p, encoding="unicode")

    logger.warning("Failed to locate the first paragraph from input_string: {}.".format(input_string))
    return ""


def iso_datetime(date):
    try:
        return date.isoformat()
    except Exception:
        logger.warning("Failed to convert datetime. Arguments: Datetime - {} into ISOFormat".format(date))
