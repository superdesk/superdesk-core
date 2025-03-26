from quart import Request, Response
from quart import request as quart_request

from authlib.integrations.flask_oauth2 import AuthorizationServer as FlaskAuthorizationServer
from authlib.oauth2.rfc6749 import UnsupportedGrantTypeError, OAuth2Error

from superdesk.core import json
from .requests import QuartOAuth2Request, QuartJsonRequest


class QuartAuthorizationServer(FlaskAuthorizationServer):
    async def create_oauth2_request(self, request):
        req = QuartOAuth2Request(quart_request)
        await req.init_request_data()
        return req

    async def create_json_request(self, request):
        req = QuartJsonRequest(quart_request)
        await req.init_request_data()
        return req

    def handle_response(self, status_code, payload, headers):
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        return Response(payload, status=status_code, headers=headers)

    async def create_token_response(self, request: Request | None = None) -> Response:
        """Validate token request and create token response.

        :param request: HTTP request instance
        """

        request = await self.create_oauth2_request(request)
        try:
            grant = self.get_token_grant(request)
        except UnsupportedGrantTypeError as error:
            return self.handle_error_response(request, error)

        try:
            grant.validate_token_request()
            args = grant.create_token_response()
            return self.handle_response(*args)
        except OAuth2Error as error:
            return self.handle_error_response(request, error)
