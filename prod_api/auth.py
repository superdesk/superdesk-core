from authlib.jose import jwt
from authlib.jose.errors import BadSignatureError
from flask import current_app as app
from eve.auth import TokenAuth


class JWTAuth(TokenAuth):
    """
    Implements JWT auth logic.
    """

    def check_auth(self, token, allowed_roles, resource, method):
        """ This function is called to check if a token is valid. Must be
        overridden with custom logic.

        :param token: token.
        :param allowed_roles: allowed user roles.
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """

        if not app.config.get('AUTH_SERVER_SHARED_SECRET'):
            return False

        try:
            decoded_jwt = jwt.decode(
                token,
                key=app.config.get('AUTH_SERVER_SHARED_SECRET')
            )
        except BadSignatureError:
            return False

        raise NotImplementedError