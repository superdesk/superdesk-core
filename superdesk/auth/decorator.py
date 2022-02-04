from typing import Optional
from functools import wraps
from flask import request
from flask import current_app as app


def blueprint_auth(resource: Optional[str] = None):
    """
    This decorator is used to add authentication to a Flask Blueprint
    """

    def fdec(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = app.auth
            if not auth.authorized([], resource or "_blueprint", request.method):
                return auth.authenticate()
            return f(*args, **kwargs)

        return decorated

    return fdec
