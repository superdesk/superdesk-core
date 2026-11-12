from copy import deepcopy
from datetime import timedelta

from bson import ObjectId

import superdesk
from superdesk.tests import TestCase, setup_db_user, test_user, token_to_basic_auth_header
from superdesk.utc import utcnow
from apps.auth.session_purge import RemoveExpiredSessions
from apps.auth.sessions import MOBILE_SESSION_TYPE

JSON = ("Content-Type", "application/json")
DEVICE = "Ana's iPhone"


def other_user(username, user_type):
    # `setup_db_user` stores the created `_id` (and etag) on the shared `test_user` dict.
    user = {key: value for key, value in deepcopy(test_user).items() if not key.startswith("_") and key != "id"}
    user.update(username=username, email=f"{username}@example.com", user_type=user_type)
    return user


class MobilePairingTestCase(TestCase):
    app_config = {"MOBILE_PAIRING_ENABLED": True}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.headers = [JSON]
        await setup_db_user(self, None)
        self.web_headers = list(self.headers)
        self.user_id = str(self.app.data.find_one("users", req=None, username=test_user["username"])["_id"])

    async def create_pairing(self, headers=None):
        response = await self.client.post("/api/mobile_pairing", json={}, headers=headers or self.web_headers)
        self.assertEqual(201, response.status_code, await response.get_data())
        return await response.get_json()

    async def get_pairing(self, pairing_id, headers=None):
        return await self.client.get(f"/api/mobile_pairing/{pairing_id}", headers=headers or self.web_headers)

    async def decide(self, pairing_id, status, headers=None):
        headers = headers or self.web_headers
        etag = (await (await self.get_pairing(pairing_id, headers)).get_json())["_etag"]
        return await self.client.patch(
            f"/api/mobile_pairing/{pairing_id}", json={"status": status}, headers=headers + [("If-Match", etag)]
        )

    async def claim(self, code, device_name=DEVICE):
        return await self.client.post(
            "/api/mobile_pairing_claim", json={"code": code, "device_name": device_name}, headers=[JSON]
        )

    async def complete(self, claim, secret=None):
        return await self.client.post(
            "/api/auth_mobile_pairing",
            json={"claim_id": claim["claim_id"], "claim_secret": secret or claim["claim_secret"]},
            headers=[JSON],
        )

    async def claimed_pairing(self):
        pairing = await self.create_pairing()
        response = await self.claim(pairing["code"])
        self.assertEqual(201, response.status_code, await response.get_data())
        return pairing, await response.get_json()

    async def stored_pairing(self, pairing_id):
        return await superdesk.get_resource_service("mobile_pairing").pairings().find_one({"_id": ObjectId(pairing_id)})

    async def expire(self, pairing_id):
        await (
            superdesk.get_resource_service("mobile_pairing")
            .pairings()
            .update_one({"_id": ObjectId(pairing_id)}, {"$set": {"expires_at": utcnow() - timedelta(seconds=1)}})
        )

    async def assertPairingError(self, response, status_code, reason):
        self.assertEqual(status_code, response.status_code, await response.get_data())
        self.assertEqual({"pairing": reason}, (await response.get_json())["_issues"])

    async def test_phone_gets_a_session_after_approval(self):
        pairing = await self.create_pairing()
        self.assertEqual("pending", pairing["status"])
        self.assertGreater(len(pairing["code"]), 40)
        self.assertTrue(55 <= pairing["expires_in"] <= 60)

        stored = await self.stored_pairing(pairing["_id"])
        self.assertNotIn("code", stored)
        self.assertNotEqual(pairing["code"], stored["code_hash"])

        response = await self.claim(pairing["code"])
        self.assertEqual(201, response.status_code, await response.get_data())
        claim = await response.get_json()
        self.assertTrue(10 <= claim["match_number"] <= 99)

        seen = await (await self.get_pairing(pairing["_id"])).get_json()
        self.assertEqual("claimed", seen["status"])
        self.assertEqual(DEVICE, seen["device_name"])
        self.assertEqual(claim["match_number"], seen["match_number"])
        for secret_field in ("code", "code_hash", "claim_id", "claim_secret_hash", "failed_attempts"):
            self.assertNotIn(secret_field, seen)

        await self.assertPairingError(await self.complete(claim), 400, "pending")

        response = await self.decide(pairing["_id"], "approved")
        self.assertEqual(200, response.status_code, await response.get_data())

        response = await self.complete(claim)
        self.assertEqual(201, response.status_code, await response.get_data())
        session = await response.get_json()
        self.assertEqual(self.user_id, session["user"])
        self.assertNotIn("claim_secret", session)

        phone_headers = [JSON, token_to_basic_auth_header(session["token"])]
        response = await self.client.get(f"/api/users/{self.user_id}", headers=phone_headers)
        self.assertEqual(200, response.status_code)

        auth = self.app.data.find_one("auth", req=None, _id=session["_id"])
        self.assertEqual(MOBILE_SESSION_TYPE, auth["session_type"])
        self.assertNotIn("claim_id", auth)
        self.assertNotIn("claim_secret", auth)

        stored = await self.stored_pairing(pairing["_id"])
        self.assertEqual("completed", stored["status"])
        self.assertEqual(str(stored["session"]), session["_id"])

        # A phone that never saw the 201 asks again and gets the same session, not a second one.
        response = await self.complete(claim)
        self.assertEqual(201, response.status_code, await response.get_data())
        repeated = await response.get_json()
        self.assertEqual((session["_id"], session["token"]), (repeated["_id"], repeated["token"]))
        self.assertEqual(
            1, self.app.data.get_mongo_collection("auth").count_documents({"session_type": MOBILE_SESSION_TYPE})
        )

        activity = self.app.data.get_mongo_collection("activity").find_one({"resource": "mobile_pairing"})
        self.assertEqual(DEVICE, activity["data"]["device_name"])

        # The phone session ends like any other one.
        response = await self.client.get(f"/api/auth/{session['_id']}", headers=phone_headers)
        response = await self.client.delete(
            f"/api/auth/{session['_id']}", headers=phone_headers + [("If-Match", (await response.get_json())["_etag"])]
        )
        self.assertEqual(204, response.status_code)

        # Signing out is final: completing again does not bring the session back.
        await self.assertPairingError(await self.complete(claim), 401, "invalid")

    async def test_repeat_complete_stops_when_the_pairing_expires(self):
        pairing, claim = await self.claimed_pairing()
        await self.decide(pairing["_id"], "approved")
        self.assertEqual(201, (await self.complete(claim)).status_code)

        await self.expire(pairing["_id"])

        await self.assertPairingError(await self.complete(claim), 401, "invalid")

    async def test_phone_session_cannot_pair_another_phone(self):
        pairing, claim = await self.claimed_pairing()
        await self.decide(pairing["_id"], "approved")
        session = await (await self.complete(claim)).get_json()

        response = await self.client.post(
            "/api/mobile_pairing", json={}, headers=[JSON, token_to_basic_auth_header(session["token"])]
        )

        self.assertEqual(403, response.status_code)

    async def test_codes_are_single_use_and_errors_do_not_tell_why(self):
        pairing, _claim = await self.claimed_pairing()
        used = await self.claim(pairing["code"])
        unknown = await self.claim("this-code-never-existed")

        other = await self.create_pairing()
        await self.expire(other["_id"])
        expired = await self.claim(other["code"])

        for response in (used, unknown, expired):
            await self.assertPairingError(response, 400, "invalid_code")
        self.assertEqual(await used.get_json(), await unknown.get_json())
        self.assertEqual(await used.get_json(), await expired.get_json())

    async def test_a_new_code_retires_the_previous_one(self):
        first = await self.create_pairing()
        await self.create_pairing()

        await self.assertPairingError(await self.claim(first["code"]), 400, "invalid_code")

    async def test_wrong_secrets_lock_the_pairing(self):
        pairing, claim = await self.claimed_pairing()
        await self.decide(pairing["_id"], "approved")

        for _attempt in range(5):
            await self.assertPairingError(await self.complete(claim, secret="wrong"), 401, "invalid")

        await self.assertPairingError(await self.complete(claim), 401, "invalid")
        self.assertEqual("failed", (await self.stored_pairing(pairing["_id"]))["status"])

    async def test_denied_phone_gets_no_session(self):
        pairing, claim = await self.claimed_pairing()

        response = await self.decide(pairing["_id"], "denied")
        self.assertEqual(200, response.status_code, await response.get_data())

        await self.assertPairingError(await self.complete(claim), 403, "denied")
        await self.assertPairingError(await self.decide(pairing["_id"], "approved"), 400, "invalid_state")

    async def test_expired_claim_can_not_be_approved_or_completed(self):
        pairing, claim = await self.claimed_pairing()
        await self.expire(pairing["_id"])

        seen = await (await self.get_pairing(pairing["_id"])).get_json()
        self.assertEqual(0, seen["expires_in"])
        await self.assertPairingError(await self.decide(pairing["_id"], "approved"), 400, "expired")
        await self.assertPairingError(await self.complete(claim), 410, "expired")

    async def test_only_the_creator_can_see_or_decide(self):
        pairing, claim = await self.claimed_pairing()
        etag = (await (await self.get_pairing(pairing["_id"])).get_json())["_etag"]

        await setup_db_user(self, other_user("other", user_type="administrator"))

        response = await self.get_pairing(pairing["_id"], self.headers)
        self.assertEqual(404, response.status_code)

        response = await self.client.patch(
            f"/api/mobile_pairing/{pairing['_id']}",
            json={"status": "approved"},
            headers=self.headers + [("If-Match", etag)],
        )
        self.assertEqual(404, response.status_code)
        await self.assertPairingError(await self.complete(claim), 400, "pending")

    async def test_creating_needs_the_privilege(self):
        await setup_db_user(self, other_user("reporter", user_type="user"))

        response = await self.client.post("/api/mobile_pairing", json={}, headers=self.headers)

        self.assertEqual(403, response.status_code)

    async def test_purge_honours_the_mobile_session_expiry(self):
        user_id = ObjectId(self.user_id)
        now = utcnow()
        web_minutes = self.app.config["SESSION_EXPIRY_MINUTES"]
        mobile_minutes = self.app.config["MOBILE_SESSION_EXPIRY_MINUTES"]
        self.assertGreater(mobile_minutes, web_minutes)

        idle = now - timedelta(minutes=web_minutes + 10)
        long_idle = now - timedelta(minutes=mobile_minutes + 10)
        ids = self.app.data.insert(
            "auth",
            [
                {"user": user_id, "token": "web-idle", "_updated": idle},
                {"user": user_id, "token": "mobile-idle", "_updated": idle, "session_type": MOBILE_SESSION_TYPE},
                {"user": user_id, "token": "mobile-gone", "_updated": long_idle, "session_type": MOBILE_SESSION_TYPE},
            ],
        )

        expired = await self.create_pairing()
        await self.expire(expired["_id"])
        live = await self.create_pairing()

        await RemoveExpiredSessions().run()

        remaining = {str(auth["_id"]) for auth in self.app.data.find_all("auth")}
        self.assertNotIn(str(ids[0]), remaining)
        self.assertIn(str(ids[1]), remaining)
        self.assertNotIn(str(ids[2]), remaining)

        self.assertIsNone(await self.stored_pairing(expired["_id"]))
        self.assertIsNotNone(await self.stored_pairing(live["_id"]))


class MobilePairingDisabledTestCase(TestCase):
    app_config = {"MOBILE_PAIRING_ENABLED": False}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.headers = [JSON]
        await setup_db_user(self, None)

    async def test_endpoints_do_not_exist(self):
        self.assertFalse(self.app.client_config["mobile_pairing"])

        response = await self.client.post("/api/mobile_pairing", json={}, headers=self.headers)
        self.assertEqual(404, response.status_code)

        response = await self.client.post(
            "/api/mobile_pairing_claim", json={"code": "code", "device_name": DEVICE}, headers=[JSON]
        )
        self.assertEqual(404, response.status_code)

        response = await self.client.post(
            "/api/auth_mobile_pairing", json={"claim_id": "claim", "claim_secret": "secret"}, headers=[JSON]
        )
        self.assertEqual(404, response.status_code)

        await RemoveExpiredSessions().run()
