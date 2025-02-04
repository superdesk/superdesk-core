from typing import Any, cast
from quart_babel import _

from superdesk.utc import utcnow
from superdesk.core.types.web import Request
from superdesk.errors import SuperdeskApiError
from superdesk.core.auth.user_auth import UserAuthProtocol
from superdesk.publish.subscriber_token import SubscriberTokenService, SubscriberToken


class SubscriberTokenAuth(UserAuthProtocol):
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
        token_missing_exception = SuperdeskApiError.forbiddenError(message=_("Authorization token missing."))
        token_id = self.get_token_from_request(request)

        if token_id is None:
            raise token_missing_exception

        token = await token_service.find_by_id(token_id)
        if token is None:
            raise token_missing_exception

        await self.check_token_validity(token)
        await self.start_session(request, None, token=token)

    async def check_token_validity(self, token: SubscriberToken) -> None:
        """
        Checks if the token is valid and if it has expired.
        """

        if token.expiry and token.expiry < utcnow():
            await SubscriberTokenService().delete(token)
            raise SuperdeskApiError.forbiddenError(message=_("Authorization token expired."))

    async def start_session(self, request: Request, user: Any, **kwargs) -> None:
        """
        Puts the subscriber id into ``g.user``.
        """
        token = cast(SubscriberToken, kwargs.get("token"))
        request.storage.request.set("user", str(token.subscriber))

    async def stop_session(self, request: Request) -> None:
        """
        Removes the subscriber id from ``g.user``.
        """
        request.storage.request.set("user", None)

    def get_current_user(self, request: Request) -> str | None:
        """Overrides as it is needed."""
        return None
