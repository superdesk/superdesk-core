from typing import Optional
from functools import wraps

from superdesk.core import get_current_app
from superdesk.flask import request


def blueprint_auth(resource: Optional[str] = None):
    """
    This decorator is used to add authentication to a Flask Blueprint
    """

    def fdec(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = get_current_app().auth
            if not auth.authorized([], resource or "_blueprint", request.method):
                return auth.authenticate()
            return f(*args, **kwargs)

        return decorated

    return fdec
