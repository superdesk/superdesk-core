from typing import Optional
from inspect import isawaitable
from functools import wraps

from superdesk.core import get_current_app
from superdesk.flask import request


def blueprint_auth(resource: Optional[str] = None):
    """
    This decorator is used to add authentication to a Flask Blueprint
    """

    def fdec(f):
        @wraps(f)
        async def decorated(*args, **kwargs):
            auth = get_current_app().auth
            if not await auth.authorized([], resource or "_blueprint", request.method):
                return auth.authenticate()
            response = f(*args, **kwargs)
            if isawaitable(response):
                response = await response
            return response

        return decorated

    return fdec
