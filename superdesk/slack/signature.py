# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from typing import Mapping

from slack_sdk.signature import SignatureVerifier

from .config import get_signing_secret


logger = logging.getLogger(__name__)


def verify_slack_request(headers: Mapping[str, str], body: bytes | str) -> bool:
    """Check the ``X-Slack-Signature`` of an incoming Slack request.

    The verifier covers the HMAC-SHA256 over ``v0:<timestamp>:<raw body>``, the five minute
    timestamp window and the constant time comparison. ``body`` must be the raw request body:
    re-serialised JSON produces a different signature.

    Returns ``False`` on any problem (no signing secret configured, missing or malformed headers)
    rather than raising, so callers can answer with a plain 401.
    """

    signing_secret = get_signing_secret()
    if not signing_secret:
        return False

    try:
        return SignatureVerifier(signing_secret).is_valid_request(body, dict(headers))
    except (ValueError, TypeError):
        return False
