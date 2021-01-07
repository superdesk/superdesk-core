# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.errors import SuperdeskApiError


class UserInactiveError(SuperdeskApiError):
    """User is inactive, access restricted"""

    status_code = 403
    payload = {"is_active": False}
    message = "Account is inactive, access restricted."


class UserNotRegisteredException(Exception):
    pass
