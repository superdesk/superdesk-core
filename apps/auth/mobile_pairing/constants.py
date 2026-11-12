# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import timedelta

PAIRING_PRIVILEGE = "mobile_pairing"

#: How long the code shown in the QR can be claimed.
CODE_TTL = timedelta(seconds=60)
#: How long the web user has to approve or deny once a phone has claimed the code.
DECISION_TTL = timedelta(seconds=120)
#: How long the phone has to collect its session once the web user approved.
COMPLETE_TTL = timedelta(seconds=60)

#: Wrong claim secrets accepted before the pairing is locked for good.
MAX_FAILED_ATTEMPTS = 5

DEVICE_NAME_MAX_LENGTH = 100


class PairingStatus:
    PENDING = "pending"
    CLAIMED = "claimed"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    FAILED = "failed"


class PairingError:
    """Machine-readable reasons, sent as ``_issues.pairing`` in error responses."""

    INVALID_CODE = "invalid_code"
    INVALID = "invalid"
    PENDING = "pending"
    DENIED = "denied"
    EXPIRED = "expired"
    INVALID_STATE = "invalid_state"
