# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
Sign in to the mobile app with a QR code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A signed-in web user creates a pairing (``POST /mobile_pairing``) and shows its one-time code as a
QR. The phone claims it with the code (``POST /mobile_pairing_claim``, public) and gets back a claim
id, a claim secret and a two digit number. The web client polls the pairing, shows the device name
and the number, and the user approves or denies it (``PATCH /mobile_pairing/<id>``). The phone polls
``POST /auth_mobile_pairing`` (public) with the claim id and secret, and once approved receives a
session created by :class:`apps.auth.service.AuthService`, exactly like ``auth_db`` returns one.

The number guards against someone who photographs the QR and claims it first: the real user's phone
then shows an error instead of the number the web client shows.

Settings: ``MOBILE_PAIRING_ENABLED`` and ``MOBILE_SESSION_EXPIRY_MINUTES``.
"""

import superdesk
from quart_babel import lazy_gettext

from .constants import PAIRING_PRIVILEGE
from .resource import MobilePairingAuthResource, MobilePairingClaimResource, MobilePairingResource
from .service import MobilePairingAuthService, MobilePairingClaimService, MobilePairingService


def init_app(app) -> None:
    enabled = bool(app.config.get("MOBILE_PAIRING_ENABLED"))
    app.client_config["mobile_pairing"] = enabled
    if not enabled:
        return

    backend = superdesk.get_backend()
    MobilePairingResource("mobile_pairing", app=app, service=MobilePairingService("mobile_pairing", backend=backend))
    MobilePairingClaimResource(
        "mobile_pairing_claim", app=app, service=MobilePairingClaimService("mobile_pairing", backend=backend)
    )
    MobilePairingAuthResource("auth_mobile_pairing", app=app, service=MobilePairingAuthService("auth", backend=backend))

    superdesk.privilege(
        name=PAIRING_PRIVILEGE,
        label=lazy_gettext("Connect mobile app"),
        description=lazy_gettext("User can sign in to the mobile app by scanning a QR code shown in Superdesk."),
    )
