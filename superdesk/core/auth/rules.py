from typing import Any

from superdesk.core.types import Request
from superdesk.errors import SuperdeskApiError


async def login_required_auth_rule(request: Request) -> None:
    if request.user is None:
        raise SuperdeskApiError.unauthorizedError()

    return None


async def endpoint_intrinsic_auth_rule(request: Request) -> Any | None:
    intrinsic_auth = getattr(request.endpoint, "authorize", None)
    if intrinsic_auth is not None:
        response = await intrinsic_auth(request)
        if response is not None:
            return response

    method = request.method.lower()
    intrinsic_auth = getattr(request.endpoint, f"authorize_{method}", None)
    if intrinsic_auth:
        response = await intrinsic_auth(request)
        if response is not None:
            return response

    return None
