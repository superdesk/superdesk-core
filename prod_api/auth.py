from time import time
from authlib.jose import jwt
from authlib.jose.errors import BadSignatureError, ExpiredTokenError, DecodeError
from flask import abort, make_response, jsonify
from flask import current_app as app
from eve.auth import TokenAuth

from superdesk import get_resource_privileges


class JWTAuth(TokenAuth):
    """
    Implements JWT auth logic.
    """

    def check_auth(self, token, allowed_roles, resource, method):
        """
        This function is called to check if a token is valid. Must be
        overridden with custom logic.

        :param token: token.
        :param allowed_roles: allowed user roles.
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """

        if not app.config.get('AUTH_SERVER_SHARED_SECRET'):
            return False

        # decode jwt
        try:
            decoded_jwt = jwt.decode(
                token,
                key=app.config.get('AUTH_SERVER_SHARED_SECRET')
            )
            decoded_jwt.validate_exp(now=time(), leeway=0)
        except (BadSignatureError, ExpiredTokenError, DecodeError):
            return False

        # authorization
        resource_privileges = get_resource_privileges(resource).get(method, None)
        if resource_privileges not in decoded_jwt.get('scope', []):
            abort(
                make_response(
                    jsonify({
                        "_status": "ERR",
                        "_error": {
                            "code": 403,
                            "message": "Invalid scope"
                        }
                    }),
                    403
                )
            )

        return True
