import base64

from typing import Any

from superdesk.core.types import Request
from superdesk.errors import SuperdeskApiError

from .user_auth import UserAuthProtocol
from .utils import set_user_request_auth_data, clear_user_request_auth_data


class TokenAuthorization(UserAuthProtocol):
    def _get_auth_token_from_request(self, request: Request) -> str | None:
        token = request.get_header("Authorization")
        if not token:
            return None

        token = token.strip()
        if token.lower().startswith(("token", "bearer", "basic")):
            token = token.split(" ")[1] if " " in token else ""

        # tokens are no longer decoded internally by flask/quart
        # so we need to do it ourselves
        return self._decode_token(token)

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
        new_session = True
        token = self._get_auth_token_from_request(request)

        if not token:
            token = request.storage.session.get("session_token")
            new_session = False

        if not token:
            await self.stop_session(request)
            raise SuperdeskApiError.unauthorizedError()

        if new_session:
            await self.start_session(request, {}, token=token)
        else:
            await self.continue_session(request, {}, token=token)

    async def continue_session(self, request: Request, user: dict[str, Any], **kwargs) -> None:
        try:
            user_dict = await set_user_request_auth_data(kwargs.get("token"), request)
            await super().continue_session(request, user_dict, **kwargs)
        except SuperdeskApiError as error:
            if error.status_code == 401:
                await self.stop_session(request)
            raise

    async def stop_session(self, request: Request) -> None:
        clear_user_request_auth_data(request)
        await super().stop_session(request)

    def get_current_user(self, request: Request) -> dict[str, Any] | None:
        user = request.storage.request.get("user")
        return user
