# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from superdesk.resource import Resource

from .constants import PAIRING_PRIVILEGE, PairingStatus


class MobilePairingResource(Resource):
    """Pairing requests created by a signed-in web user, read and decided by that user only.

    The hashes and the claim id are kept out of the schema on purpose: Eve projects responses onto
    the schema fields, so they never leave the server through this resource.
    """

    schema = {
        # The only field a client may write: the web user's decision on a claimed pairing.
        "status": {"type": "string", "allowed": [PairingStatus.APPROVED, PairingStatus.DENIED]},
        "user": Resource.rel("users", embeddable=False, readonly=True),
        "expires_at": {"type": "datetime", "readonly": True},
        "device_name": {"type": "string", "readonly": True, "nullable": True},
        "match_number": {"type": "integer", "readonly": True, "nullable": True},
        # Response only: the code is returned once by POST and never stored, expires_in is computed.
        "code": {"type": "string", "readonly": True},
        "expires_in": {"type": "integer", "readonly": True},
    }
    datasource = {"source": "mobile_pairing"}
    resource_methods = ["POST"]
    item_methods = ["GET", "PATCH"]
    privileges = {"POST": PAIRING_PRIVILEGE, "PATCH": PAIRING_PRIVILEGE}
    extra_response_fields = ["status", "code", "expires_at", "expires_in"]
    notifications = False
    mongo_indexes = {
        "code_hash_1": ([("code_hash", 1)], {"sparse": True}),
        "claim_id_1": ([("claim_id", 1)], {"sparse": True}),
        "user_1_status_1": ([("user", 1), ("status", 1)], {}),
        "expires_at_1": ([("expires_at", 1)], {}),
    }

    async def pre_request_patch_async(self, request, lookup) -> None:
        payload = await request.get_json(silent=True)
        await get_resource_service(self.endpoint_name).validate_decision(lookup.get("_id"), payload)


class MobilePairingClaimResource(Resource):
    """Public: the phone exchanges the code from the QR for a claim it can complete later."""

    schema = {
        "code": {"type": "string", "required": True, "empty": False, "maxlength": 256},
        "device_name": {"type": "string", "required": True, "empty": False, "maxlength": 256},
        # Response only.
        "claim_id": {"type": "string", "readonly": True},
        "claim_secret": {"type": "string", "readonly": True},
        "match_number": {"type": "integer", "readonly": True},
        "expires_in": {"type": "integer", "readonly": True},
    }
    datasource = {"source": "mobile_pairing"}
    resource_methods = ["POST"]
    item_methods = []
    public_methods = ["POST"]
    extra_response_fields = ["claim_id", "claim_secret", "match_number", "expires_in"]
    notifications = False


class MobilePairingAuthResource(Resource):
    """Public: the phone exchanges an approved claim for a session, like ``auth_db`` does for a password."""

    schema = {
        "claim_id": {"type": "string", "required": True, "empty": False, "maxlength": 256},
        "claim_secret": {"type": "string", "required": True, "empty": False, "maxlength": 256},
        "token": {"type": "string"},
        "user": Resource.rel("users", True),
    }
    datasource = {"source": "auth"}
    resource_methods = ["POST"]
    item_methods = []
    public_methods = ["POST"]
    extra_response_fields = ["user", "token", "username"]
