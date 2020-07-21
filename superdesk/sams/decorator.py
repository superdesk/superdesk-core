from functools import wraps
from flask import request


def blueprint_auth(app):
    def fdec(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = app.auth
            if not auth.authorized([], '_blueprint', request.method):
                return auth.authenticate()
            return f(*args, **kwargs)
        return decorated
    return fdec
