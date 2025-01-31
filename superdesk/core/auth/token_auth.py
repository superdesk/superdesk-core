import base64
import arrow

from typing import Any, cast
from datetime import timedelta

from superdesk.utc import utcnow
from superdesk.core import json, get_app_config
from superdesk.core.types import Request
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.resource_fields import LAST_UPDATED, ID_FIELD

from .user_auth import UserAuthProtocol


class TokenAuthorization(UserAuthProtocol):
    @staticmethod
    def _decode_token(token: str) -> str:
        """
        Tries to decode the auth header token. Decode logic based on internal logic from
        `werkzeug.datastructures.Authorization`
        """
        try:
            return base64.b64decode(token).decode().partition(":")[0]
        except Exception:
            return token

    async def authenticate(self, request: Request):
        token = request.get_header("Authorization")
        new_session = True

        if token:
            token = token.strip()
            if token.lower().startswith(("token", "bearer", "basic")):
                token = token.split(" ")[1] if " " in token else ""
        else:
            token = request.storage.session.get("session_token")
            new_session = False

        if not token:
            await self.stop_session(request)
            raise SuperdeskApiError.unauthorizedError()

        # Check provided token is valid
        auth_service = get_resource_service("auth")

        # tokens are no longer decoded internally by flask/quart
        # so we need to do it ourselves
        token = self._decode_token(token)
        auth_token = auth_service.find_one(token=token, req=None)

        if not auth_token:
            await self.stop_session(request)
            raise SuperdeskApiError.unauthorizedError()

        user_service = get_resource_service("users")
        user_id = str(auth_token["user"])
        user = user_service.find_one(req=None, _id=user_id)

        if not user:
            await self.stop_session(request)
            raise SuperdeskApiError.unauthorizedError()

        if new_session:
            await self.start_session(request, user, auth_token=auth_token)
        else:
            await self.continue_session(request, user)

    async def start_session(self, request: Request, user: dict[str, Any], **kwargs) -> None:
        auth_token: str | None = kwargs.pop("auth_token", None)
        if not auth_token:
            await self.stop_session(request)
            raise SuperdeskApiError.unauthorizedError()

        request.storage.session.set("session_token", json.dumps(auth_token))
        await super().start_session(request, user, **kwargs)

    async def continue_session(self, request: Request, user: dict[str, Any], **kwargs) -> None:
        auth_token = request.storage.session.get("session_token")

        if isinstance(auth_token, str):
            auth_token = json.loads(auth_token)

        if not auth_token:
            await self.stop_session(request)
            raise SuperdeskApiError.unauthorizedError()

        user_service = get_resource_service("users")
        request.storage.request.set("user", user)
        request.storage.request.set("role", user_service.get_role(user))
        request.storage.request.set("auth", auth_token)
        request.storage.request.set("auth_value", auth_token["user"])

        if request.method in ("POST", "PUT", "PATCH") or (request.method == "GET" and not request.get_url_arg("auto")):
            now = utcnow()
            auth_updated = False
            session_update_seconds = cast(int, get_app_config("SESSION_UPDATE_SECONDS", 30))
            auth_last_updated = arrow.get(auth_token[LAST_UPDATED])

            if auth_last_updated + timedelta(seconds=session_update_seconds) < now:
                auth_service = get_resource_service("auth")
                auth_service.update_session({LAST_UPDATED: now})
                auth_updated = True
            if auth_updated or not request.storage.request.get("last_activity_at"):
                user_service.system_update(user[ID_FIELD], {"last_activity_at": now, "_updated": now}, user)

        await super().continue_session(request, user, **kwargs)

    def get_current_user(self, request: Request) -> dict[str, Any] | None:
        user = request.storage.request.get("user")
        return user
