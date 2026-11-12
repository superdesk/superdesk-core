"""Mobile pairing logic against an in-memory pairing collection.

The flows through the real API, Mongo and sessions are in ``mobile_pairing_test.py``.
"""

from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from quart_babel import Babel

from superdesk.errors import SuperdeskApiError
from superdesk.tests import AsyncQuartTestCase
from superdesk.utc import utcnow
from apps.auth.mobile_pairing.constants import MAX_FAILED_ATTEMPTS, PairingStatus
from apps.auth.mobile_pairing.service import (
    PAIRING_ID,
    REPLAYED_SESSION,
    MobilePairingAuthService,
    MobilePairingClaimService,
    MobilePairingService,
    clean_device_name,
    hash_secret,
    secret_matches,
    seconds_left,
)
from apps.auth.sessions import MOBILE_SESSION_TYPE

SERVICE = "apps.auth.mobile_pairing.service"


def matches(doc: dict, query: dict) -> bool:
    for key, condition in query.items():
        value = doc.get(key)
        if isinstance(condition, dict):
            for operator, operand in condition.items():
                if operator == "$gt" and not (value is not None and value > operand):
                    return False
                if operator == "$lte" and not (value is not None and value <= operand):
                    return False
        elif value != condition:
            return False
    return True


class FakeCollection:
    """Just enough of a Motor collection for the pairing services."""

    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query):
        found = next((doc for doc in self.docs if matches(doc, query)), None)
        return deepcopy(found)

    async def find_one_and_update(self, query, update, return_document=None):
        doc = next((doc for doc in self.docs if matches(doc, query)), None)
        if doc is None:
            return None
        doc.update(update.get("$set", {}))
        for key, increment in update.get("$inc", {}).items():
            doc[key] = doc.get(key, 0) + increment
        return deepcopy(doc)

    async def update_many(self, query, update):
        for doc in self.docs:
            if matches(doc, query):
                doc.update(update.get("$set", {}))

    async def delete_many(self, query):
        before = len(self.docs)
        self.docs = [doc for doc in self.docs if not matches(doc, query)]
        return SimpleNamespace(deleted_count=before - len(self.docs))


def backend_for(collection: FakeCollection):
    backend = MagicMock()
    backend.get_mongo_collection_async.return_value = collection
    return backend


def claimed_pairing(user_id, secret="the-secret", status=PairingStatus.CLAIMED, expires_in=60, **extra):
    return {
        "_id": ObjectId(),
        "user": user_id,
        "status": status,
        "claim_id": "claim-1",
        "claim_secret_hash": hash_secret(secret),
        "expires_at": utcnow() + timedelta(seconds=expires_in),
        "failed_attempts": 0,
        **extra,
    }


class PairingTestCase(AsyncQuartTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        Babel(self.app)


class HelpersTestCase(PairingTestCase):
    async def test_secret_matches(self):
        stored = hash_secret("secret")
        self.assertTrue(secret_matches("secret", stored))
        self.assertFalse(secret_matches("Secret", stored))
        self.assertFalse(secret_matches(None, stored))
        self.assertFalse(secret_matches("secret", None))

    async def test_seconds_left_rounds_up_and_never_goes_negative(self):
        now = utcnow()
        self.assertEqual(30, seconds_left(now + timedelta(seconds=30), now))
        self.assertEqual(1, seconds_left(now + timedelta(milliseconds=200), now))
        self.assertEqual(0, seconds_left(now, now))
        self.assertEqual(0, seconds_left(now - timedelta(seconds=30), now))
        self.assertEqual(0, seconds_left(None, now))

    async def test_clean_device_name(self):
        self.assertEqual("Ana's iPhone", clean_device_name("  Ana's\n\tiPhone ‮ "))
        self.assertEqual(100, len(clean_device_name("x" * 500)))
        self.assertEqual("", clean_device_name("\u0000​"))


class ClaimTestCase(PairingTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.pending = {
            "_id": ObjectId(),
            "user": ObjectId(),
            "status": PairingStatus.PENDING,
            "code_hash": hash_secret("the-code"),
            "expires_at": utcnow() + timedelta(seconds=60),
            "_etag": "before-claim",
        }
        self.collection = FakeCollection([self.pending])
        self.service = MobilePairingClaimService("mobile_pairing", backend=backend_for(self.collection))

    async def claim(self, code="the-code", device_name="Pixel 9"):
        doc = {"code": code, "device_name": device_name}
        await self.service.create_async([doc])
        return doc

    async def assertInvalidCode(self, **kwargs):
        with self.assertRaises(SuperdeskApiError) as context:
            await self.claim(**kwargs)
        self.assertEqual(400, context.exception.status_code)
        self.assertEqual({"pairing": "invalid_code"}, context.exception.payload)

    async def test_claim_returns_claim_and_stores_only_hashes(self):
        doc = await self.claim()

        self.assertEqual(self.pending["_id"], doc["_id"])
        self.assertNotIn("code", doc)
        self.assertTrue(10 <= doc["match_number"] <= 99)
        self.assertGreater(len(doc["claim_secret"]), 40)
        self.assertGreater(doc["expires_in"], 60)

        stored = self.collection.docs[0]
        self.assertEqual(PairingStatus.CLAIMED, stored["status"])
        self.assertEqual("Pixel 9", stored["device_name"])
        self.assertEqual(doc["claim_id"], stored["claim_id"])
        self.assertEqual(hash_secret(doc["claim_secret"]), stored["claim_secret_hash"])
        self.assertNotIn("claim_secret", stored)
        self.assertNotEqual("before-claim", stored["_etag"])

    async def test_code_is_single_use(self):
        await self.claim()
        await self.assertInvalidCode()

    async def test_unknown_and_expired_codes_get_the_same_answer(self):
        await self.assertInvalidCode(code="not-a-code")
        self.pending["expires_at"] = utcnow() - timedelta(seconds=1)
        await self.assertInvalidCode()

    async def test_device_name_is_required(self):
        await self.assertInvalidCode(device_name="​")
        self.assertEqual(PairingStatus.PENDING, self.collection.docs[0]["status"])


class CompleteTestCase(PairingTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.user = {"_id": ObjectId(), "username": "foo", "is_active": True, "is_enabled": True}
        self.collection = FakeCollection()
        self.service = MobilePairingAuthService("auth", backend=backend_for(self.collection))
        self.session = {"_id": ObjectId(), "user": self.user["_id"], "token": "the-token"}
        users_service = MagicMock()
        users_service.find_one_async = AsyncMock(return_value=self.user)
        self.auth_service = MagicMock()
        self.auth_service.find_one_async = AsyncMock(return_value=self.session)
        services = {"users": users_service, "auth": self.auth_service}
        patcher = patch(f"{SERVICE}.get_resource_service", side_effect=services.__getitem__)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def complete(self, secret="the-secret"):
        credentials = {"claim_id": "claim-1", "claim_secret": secret}
        await self.service.authenticate(credentials)
        return credentials

    def add(self, **kwargs):
        pairing = claimed_pairing(self.user["_id"], **kwargs)
        self.collection.docs.append(pairing)
        return pairing

    async def assertRejected(self, status_code, reason, secret="the-secret", claim_id="claim-1"):
        with self.assertRaises(SuperdeskApiError) as context:
            await self.service.authenticate({"claim_id": claim_id, "claim_secret": secret})
        self.assertEqual(status_code, context.exception.status_code)
        self.assertEqual({"pairing": reason}, context.exception.payload)

    async def test_approved_claim_returns_the_user_and_completes(self):
        pairing = self.add(status=PairingStatus.APPROVED)

        credentials = {"claim_id": "claim-1", "claim_secret": "the-secret"}
        user = await self.service.authenticate(credentials)

        self.assertEqual(self.user["_id"], user["_id"])
        self.assertEqual(PairingStatus.COMPLETED, self.collection.docs[0]["status"])
        self.assertEqual(pairing["_id"], credentials[PAIRING_ID])
        self.assertNotIn(REPLAYED_SESSION, credentials)

    async def test_repeat_complete_returns_the_same_session(self):
        self.add(status=PairingStatus.COMPLETED, session=self.session["_id"])

        credentials = await self.complete()

        self.assertEqual(self.session, credentials[REPLAYED_SESSION])
        self.assertNotIn(PAIRING_ID, credentials)
        self.auth_service.find_one_async.assert_awaited_once_with(req=None, _id=self.session["_id"])

    async def test_repeat_complete_while_the_session_is_being_created_waits(self):
        self.add(status=PairingStatus.COMPLETED)
        await self.assertRejected(400, "pending")

    async def test_repeat_complete_does_not_revive_an_ended_session(self):
        self.add(status=PairingStatus.COMPLETED, session=ObjectId())
        self.auth_service.find_one_async.return_value = None
        await self.assertRejected(401, "invalid")

    async def test_repeat_complete_ends_with_the_pairing(self):
        self.add(status=PairingStatus.COMPLETED, session=self.session["_id"], expires_in=-1)
        await self.assertRejected(401, "invalid")

    async def test_wrong_secrets_after_completion_still_lock(self):
        self.add(status=PairingStatus.COMPLETED, session=self.session["_id"])
        for _attempt in range(MAX_FAILED_ATTEMPTS):
            await self.assertRejected(401, "invalid", secret="wrong")
        await self.assertRejected(401, "invalid")

    async def test_replayed_session_is_returned_as_is(self):
        doc = {"claim_id": "claim-1", "claim_secret": "the-secret", REPLAYED_SESSION: self.session}
        self.service.set_auth_default(doc, self.user["_id"])

        self.assertEqual(self.session["_id"], doc["_id"])
        self.assertEqual("the-token", doc["token"])

        with patch(f"{SERVICE}.AuthService.create_async", new_callable=AsyncMock) as insert:
            ids = await self.service.create_async([doc])

        insert.assert_not_awaited()
        self.assertEqual([self.session["_id"]], ids)
        self.assertNotIn(REPLAYED_SESSION, doc)

    async def test_new_session_id_is_kept_on_the_pairing(self):
        pairing = self.add(status=PairingStatus.COMPLETED)
        doc = {"token": "t", PAIRING_ID: pairing["_id"]}
        session_id = ObjectId()

        with patch(f"{SERVICE}.AuthService.create_async", new_callable=AsyncMock, return_value=[session_id]):
            ids = await self.service.create_async([doc])

        self.assertEqual([session_id], ids)
        self.assertEqual(session_id, pairing["session"])
        self.assertNotIn(PAIRING_ID, doc)

    async def test_waiting_denied_and_expired(self):
        pairing = self.add()
        await self.assertRejected(400, "pending")

        pairing["status"] = PairingStatus.DENIED
        await self.assertRejected(403, "denied")

        pairing["status"] = PairingStatus.APPROVED
        pairing["expires_at"] = utcnow() - timedelta(seconds=1)
        await self.assertRejected(410, "expired")

    async def test_state_is_only_revealed_with_the_right_secret(self):
        self.add(status=PairingStatus.DENIED)
        await self.assertRejected(401, "invalid", secret="wrong")
        await self.assertRejected(401, "invalid", claim_id="unknown")
        await self.assertRejected(401, "invalid", secret=None)

    async def test_wrong_secrets_lock_the_pairing(self):
        self.add(status=PairingStatus.APPROVED)
        for _attempt in range(MAX_FAILED_ATTEMPTS):
            await self.assertRejected(401, "invalid", secret="wrong")

        self.assertEqual(PairingStatus.FAILED, self.collection.docs[0]["status"])
        await self.assertRejected(401, "invalid")

    async def test_session_is_marked_mobile_and_drops_the_claim(self):
        doc = {"claim_id": "claim-1", "claim_secret": "the-secret"}
        self.service.set_auth_default(doc, self.user["_id"])

        self.assertEqual(MOBILE_SESSION_TYPE, doc["session_type"])
        self.assertEqual(self.user["_id"], doc["user"])
        self.assertTrue(doc["token"])
        self.assertNotIn("claim_id", doc)
        self.assertNotIn("claim_secret", doc)


class DecideTestCase(PairingTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.user_id = ObjectId()
        self.collection = FakeCollection()
        self.service = MobilePairingService("mobile_pairing", backend=backend_for(self.collection))
        for name, value in (("get_user_id", self.user_id), ("get_auth", {"_id": ObjectId()})):
            patcher = patch(f"{SERVICE}.{name}", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def assertRefused(self, original, decision, status_code, reason=None):
        with self.assertRaises(SuperdeskApiError) as context:
            await self.service.on_update_async({"status": decision}, original)
        self.assertEqual(status_code, context.exception.status_code)
        if reason:
            self.assertEqual({"pairing": reason}, context.exception.payload)

    async def test_approve_a_claimed_pairing_extends_it_for_completion(self):
        original = claimed_pairing(self.user_id, expires_in=5)
        updates = {"status": PairingStatus.APPROVED}

        await self.service.on_update_async(updates, original)

        self.assertGreater(updates["expires_at"], original["expires_at"])

    async def test_approve_needs_a_claim_that_has_not_expired(self):
        await self.assertRefused(
            claimed_pairing(self.user_id, status=PairingStatus.PENDING), "approved", 400, "invalid_state"
        )
        await self.assertRefused(claimed_pairing(self.user_id, expires_in=-1), "approved", 400, "expired")
        await self.assertRefused(
            claimed_pairing(self.user_id, status=PairingStatus.DENIED), "approved", 400, "invalid_state"
        )

    async def test_deny_works_before_and_after_the_claim_only(self):
        for status in (PairingStatus.PENDING, PairingStatus.CLAIMED):
            await self.service.on_update_async({"status": "denied"}, claimed_pairing(self.user_id, status=status))
        await self.assertRefused(
            claimed_pairing(self.user_id, status=PairingStatus.COMPLETED), "denied", 400, "invalid_state"
        )

    async def test_other_users_cannot_decide(self):
        await self.assertRefused(claimed_pairing(ObjectId()), "approved", 404)

    async def test_mobile_sessions_cannot_create_or_decide(self):
        with patch(f"{SERVICE}.get_auth", return_value={"session_type": MOBILE_SESSION_TYPE}):
            await self.assertRefused(claimed_pairing(self.user_id), "approved", 403)
            with self.assertRaises(SuperdeskApiError) as context:
                await self.service.on_create_async([{}])
            self.assertEqual(403, context.exception.status_code)

    async def test_create_retires_the_previous_unclaimed_code(self):
        previous = claimed_pairing(self.user_id, status=PairingStatus.PENDING)
        someone_else = claimed_pairing(ObjectId(), status=PairingStatus.PENDING)
        claimed = claimed_pairing(self.user_id)
        self.collection.docs.extend([previous, someone_else, claimed])
        doc: dict = {"status": "approved"}

        await self.service.on_create_async([doc])

        self.assertEqual(PairingStatus.DENIED, previous["status"])
        self.assertEqual(PairingStatus.PENDING, someone_else["status"])
        self.assertEqual(PairingStatus.CLAIMED, claimed["status"])
        self.assertEqual(PairingStatus.PENDING, doc["status"])
        self.assertEqual(self.user_id, doc["user"])

    async def test_remove_expired(self):
        expired = claimed_pairing(self.user_id, expires_in=-1)
        live = claimed_pairing(self.user_id)
        self.collection.docs.extend([expired, live])

        await self.service.remove_expired()

        self.assertEqual([live["_id"]], [doc["_id"] for doc in self.collection.docs])

    async def test_validate_decision_runs_the_same_checks_before_the_patch(self):
        expired = claimed_pairing(self.user_id, expires_in=-1)
        self.service.find_one_async = AsyncMock(return_value=expired)  # type: ignore[method-assign]
        with self.assertRaises(SuperdeskApiError) as context:
            await self.service.validate_decision(str(expired["_id"]), {"status": "approved"})
        self.assertEqual({"pairing": "expired"}, context.exception.payload)

        with self.assertRaises(SuperdeskApiError):
            await self.service.validate_decision(str(expired["_id"]), "not a dict")

        self.service.find_one_async = AsyncMock(return_value=None)  # type: ignore[method-assign]
        await self.service.validate_decision(str(ObjectId()), {"status": "approved"})
