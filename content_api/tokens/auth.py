from eve.auth import TokenAuth

from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError
from superdesk.core.types.web import AuthRule, Request
from superdesk.core.auth.user_auth import UserAuthProtocol
from superdesk.core.auth.rules import endpoint_intrinsic_auth_rule
from superdesk.publish.subscriber_token import SubscriberTokenService, SubscriberToken


# TODO-ASYNC: Needed to avoid the content_api items endpoint from crashing
# as it relies on the `user` stored in the `g` object. Once items are migrated
# we should remove this
class LegacyTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        """Try to find auth token and if valid put subscriber id into ``g.user``."""
        from superdesk.flask import g

        data = SubscriberTokenService().mongo.find_one(token)
        if not data:
            return False
        now = utcnow()
        if data.get("expiry") and data.get("expiry") < now:
            SubscriberTokenService().mongo.delete_one({"_id": token})
            return False
        g.user = str(data.get("subscriber"))
        return g.user


class SubscriberTokenAuth(UserAuthProtocol):
    def get_default_auth_rules(self) -> list[AuthRule]:
        return [endpoint_intrinsic_auth_rule]

    def get_token_from_request(self, request: Request) -> str | None:
        """
        Extracts the token from `Authorization` header. Code taken partly
        from eve.Auth module
        """

        auth = (request.get_header("Authorization") or "").strip()
        if len(auth):
            if auth.lower().startswith(("token", "bearer", "basic")):
                return auth.split(" ")[1] if " " in auth else None
            return auth

        return None

    async def authenticate(self, request: Request) -> None:
        """
        Tries to find the auth token in the request and if valid put subscriber id into ``g.user``.
        """
        token_service = SubscriberTokenService()
        token_missing_exception = SuperdeskApiError.forbiddenError(message="Authorization token missing.")
        token_id = self.get_token_from_request(request)

        if token_id is None:
            raise token_missing_exception

        token = await token_service.find_by_id(token_id)
        if token is None:
            await self.stop_session(request)
            raise token_missing_exception

        await self.check_token_validity(token)
        await self.start_session(request, token)

    async def check_token_validity(self, token: SubscriberToken) -> None:
        """
        Checks if the token is valid and if it has expired.
        """

        if token.expiry and token.expiry < utcnow():
            await SubscriberTokenService().delete(token)
            raise SuperdeskApiError.forbiddenError(message="Authorization token expired.")

    async def start_session(self, request: Request, token: SubscriberToken) -> None:  # type: ignore[override]
        """
        Puts the subscriber id into ``g.user``.
        """
        request.storage.request.set("user", str(token.subscriber))

    async def stop_session(self, request: Request) -> None:
        """
        Removes the subscriber id from ``g.user``.
        """
        request.storage.request.set("user", None)

    def get_current_user(self, request: Request) -> str | None:
        """Overrides as it is needed."""
        return None
