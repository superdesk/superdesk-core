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
import logging
from flask import json


logger = logging.getLogger(__name__)


class UserDisabledError(SuperdeskApiError):
    """User is disabled, access restricted"""

    status_code = 403
    payload = {"is_enabled": False}
    message = "Account is disabled, access restricted."


class PasswordExpiredError(SuperdeskApiError):
    """The password of the user has expired"""

    status_code = 403
    payload = {"password_is_expired": True}
    message = "The password of the user has expired."


class CredentialsAuthError(SuperdeskApiError):
    """Credentials Not Match Auth Exception"""

    def __init__(self, credentials, message=None, error=None):
        super().__init__(status_code=401, message=message, payload={"credentials": 1})
        # pop the password so that it doesn't get logged
        credentials.pop("password", None)
        logger.warning("Login failure: %s" % json.dumps(credentials))
        if error:
            logger.error("Exception occurred: {}".format(error))
