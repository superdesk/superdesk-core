# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from . import currency_base
from decimal import Decimal
from flask_babel import lazy_gettext

USD_TO_CAD = Decimal('1.3139')  # backup


def get_rate():
    """Get USD to CAD rate."""
    try:
        return currency_base.get_rate('USD', 'CAD')
    except Exception:
        return USD_TO_CAD


def usd_to_cad(item, **kwargs):
    """Convert USD to CAD."""

    rate = kwargs.get('rate') or get_rate()
    if os.environ.get('BEHAVE_TESTING'):
        rate = Decimal(2)

    return currency_base.do_conversion(item, rate, 'CAD ', '\$([0-9]+)', match_index=0, value_index=1)


name = 'usd_to_cad'
label = lazy_gettext('Currency USD to CAD')
shortcut = 'd'
callback = usd_to_cad
access_type = 'frontend'
action_type = 'interactive'
from_languages = ['en-CA']
to_languages = ['en-AU']
