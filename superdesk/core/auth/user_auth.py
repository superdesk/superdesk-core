from typing import Any, cast

from superdesk.errors import SuperdeskApiError
from superdesk.core.types import Request, AuthRule


class UserAuthProtocol:
    async def authenticate(self, request: Request) -> Any | None:
        raise SuperdeskApiError.unauthorizedError()

    async def authorize(self, request: Request) -> Any | None:
        endpoint_rules = request.endpoint.get_auth_rules()
        if endpoint_rules is False:
            # This is a public facing endpoint
            # Meaning Authentication & Authorization is disabled
            return None
        elif isinstance(endpoint_rules, dict):
            endpoint_rules = cast(list[AuthRule], endpoint_rules.get(request.method) or [])

        from .rules import login_required_auth_rule, endpoint_intrinsic_auth_rule

        default_rules: list[AuthRule] = [
            login_required_auth_rule,
            endpoint_intrinsic_auth_rule,
        ]

        for rule in default_rules + (endpoint_rules or []):
            response = await rule(request)
            if response is not None:
                return response

        return None

    async def start_session(self, request: Request, user: Any, **kwargs) -> None:
        await self.continue_session(request, user, **kwargs)

    async def continue_session(self, request: Request, user: Any, **kwargs) -> None:
        request.user = user

    async def stop_session(self, request: Request) -> None:
        pass

    def get_current_user(self, request: Request) -> Any | None:
        raise NotImplementedError()
