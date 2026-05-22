from typing import Optional
from inspect import isawaitable
from functools import wraps

from quart_babel import gettext as _

from superdesk.core import get_current_app
from superdesk.flask import request


async def _call_and_await(f, *args, **kwargs):
    response = f(*args, **kwargs)
    if isawaitable(response):
        response = await response
    return response


async def _check_session_auth(resource: Optional[str] = None):
    auth = get_current_app().auth
    if not await auth.authorized([], resource or "_blueprint", request.method):
        return auth.authenticate()
    return None


def blueprint_auth(resource: Optional[str] = None):
    """
    This decorator is used to add authentication to a Flask Blueprint
    """

    def fdec(f):
        @wraps(f)
        async def decorated(*args, **kwargs):
            auth_response = await _check_session_auth(resource)
            if auth_response:
                return auth_response
            return await _call_and_await(f, *args, **kwargs)

        return decorated

    return fdec


def blueprint_token():
    """Decorator that requires JWT token authentication via query param.

    Token must contain '_url_path' matching the current request path.

    See Also:
        superdesk.auth.utils.generate_url_with_token: Helper to generate URLs with token.
    """

    def fdec(f):
        @wraps(f)
        async def decorated(*args, **kwargs):
            from superdesk.utils import jwt_decode
            from superdesk.errors import SuperdeskApiError

            if not (token := request.args.get("token")):
                raise SuperdeskApiError.unauthorizedError(_("Token required"))

            if not (payload := jwt_decode(token)):
                raise SuperdeskApiError.unauthorizedError(_("Invalid or expired token"))

            if payload.get("_url_path") != request.path:
                raise SuperdeskApiError.unauthorizedError(_("Token not valid for this URL"))

            return await _call_and_await(f, *args, **kwargs)

        return decorated

    return fdec
