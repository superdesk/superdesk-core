from datetime import timedelta

import arrow
from quart import g, session, Request as QuartRequest

from superdesk.core.types import Request as SuperdeskRequest
from superdesk.core import get_config
from superdesk import get_resource_service
from superdesk.utc import utcnow
from superdesk.resource_fields import LAST_UPDATED
from superdesk.errors import SuperdeskApiError


async def set_user_request_auth_data(auth_token: str | None, request: SuperdeskRequest | QuartRequest) -> dict:
    """Set user, role and auth data on the request and session storage.

    :param auth_token: Auth token, from the Authorization header or the session cookie.
    :param request: Superdesk Core or Quart request instance
    :returns: A dictionary of the ``user`` resource for the current user
    :raises SuperdeskApiError.unauthorizedError: If the auth token is invalid or the user is not found.
    """

    if not auth_token:
        raise SuperdeskApiError.unauthorizedError()

    user_service = get_resource_service("users")
    auth_service = get_resource_service("auth")

    # Using the supplied token, get the ``auth`` and ``user`` docs
    auth_data = await auth_service.find_one_async(token=auth_token, req=None)
    if not auth_data:
        raise SuperdeskApiError.unauthorizedError()

    user_id = auth_data.get("user")
    if not user_id:
        raise SuperdeskApiError.unauthorizedError()

    user_dict = await user_service.find_one_async(req=None, _id=user_id)
    if not user_dict:
        raise SuperdeskApiError.unauthorizedError()

    # Get the user role and apply privileges to the user doc
    user_role = await user_service.get_role(user_dict)
    user_service.set_privileges(user_dict, user_role)

    # Store user, role and auth data on the request and session storage
    if isinstance(request, QuartRequest):
        # Superdesk Core request instance not available, use Quart directly
        if session.get("session_token") != auth_token:
            session["session_token"] = auth_token

        # Ignore types here, as quart.g is a proxy object and doesn't support type hints
        g.user = user_dict  # type: ignore[attr-defined]
        g.role = user_role  # type: ignore[attr-defined]
        g.auth = auth_data  # type: ignore[attr-defined]
        g.auth_value = user_id  # type: ignore[attr-defined]
    else:
        # Use a Superdesk Core request instance (which indirectly uses Quart)
        if request.storage.session.get("session_token") != auth_token:
            request.storage.session.set("session_token", auth_token)

        request.storage.request.set("user", user_dict)
        request.storage.request.set("role", user_role)
        request.storage.request.set("auth", auth_data)
        request.storage.request.set("auth_value", user_id)

    # Update the user's last activity time if necessary
    auto = request.args.get("auto") if isinstance(request, QuartRequest) else request.get_url_arg("auto")
    if request.method in ("POST", "PUT", "PATCH") or (request.method == "GET" and not auto):
        now = utcnow()
        auth_updated = False
        session_update_seconds = get_config(int, "SESSION_UPDATE_SECONDS")
        auth_last_updated = arrow.get(auth_data[LAST_UPDATED])

        if auth_last_updated + timedelta(seconds=session_update_seconds) < now:
            await auth_service.update_session({LAST_UPDATED: now})
            auth_updated = True

        if auth_updated or not user_dict.get("last_activity_at"):
            user_service.system_update(user_id, {"last_activity_at": now, "_updated": now}, user_dict)

    return user_dict


def clear_user_request_auth_data(request: SuperdeskRequest | QuartRequest) -> None:
    """Clear user, role and auth data from the request and session storage.

    Removes all session and request data stored by ``set_user_request_auth_data``.

    :param request: Superdesk Core or Quart request instance
    """

    if isinstance(request, QuartRequest):
        session.pop("session_token", None)
        g.pop("user", None)
        g.pop("role", None)
        g.pop("auth", None)
        g.pop("auth_value", None)
    else:
        request.storage.session.pop("session_token", None)
        request.storage.request.pop("user", None)
        request.storage.request.pop("role", None)
        request.storage.request.pop("auth", None)
        request.storage.request.pop("auth_value", None)
