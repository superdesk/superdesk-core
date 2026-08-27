from typing import cast

from pydantic import ValidationError
from quart_babel import gettext

from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.resources import ResourceRestEndpoints
from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error
from superdesk.core.types import Request, Response
from superdesk.core.web import Endpoint
from superdesk.errors import SuperdeskApiError

from .errors import AIProviderError, to_api_error
from .models import AIAction, AIProvider, RunActionPayload
from .privileges import AI_PRIVILEGE
from .providers import get_client
from .service import AIActionsService


class AIProvidersEndpoints(ResourceRestEndpoints):
    """Adds the routes an administrator needs to check a provider before saving actions against it"""

    def add_endpoints(self):
        super().add_endpoints()
        self.endpoints.append(
            Endpoint(
                url=f"{self.get_item_url()}/models",
                name="ai_provider_models",
                func=self.list_models,
                methods=["GET"],
                parent=self,
            )
        )
        self.endpoints.append(
            Endpoint(
                url=f"{self.get_item_url()}/test",
                name="ai_provider_test",
                func=self.test_connection,
                methods=["POST"],
                parent=self,
            )
        )

    async def list_models(self, request: Request) -> Response:
        provider = await self._get_provider(request)

        try:
            models = await get_client(provider).list_models()
        except AIProviderError as error:
            raise to_api_error(error)

        return Response(body={"models": models}, status_code=200)

    async def test_connection(self, request: Request) -> Response:
        """Report whether the provider answers, as a 200 with the outcome in the body.

        A provider that cannot be reached is an expected answer here, not a failed request, so the
        client can show it next to the form instead of handling an error status.
        """

        provider = await self._get_provider(request)
        result = await get_client(provider).test_connection()

        return Response(
            body={"ok": result.ok, "models_count": result.models_count, "error": result.error},
            status_code=200,
        )

    async def _get_provider(self, request: Request) -> AIProvider:
        item_id = request.get_view_args("item_id")
        provider = await self.service.find_by_id(item_id) if item_id else None

        if provider is None:
            raise SuperdeskApiError.notFoundError(
                gettext("AI provider with ID '{provider_id}' not found").format(provider_id=item_id)
            )

        return provider


class AIActionsEndpoints(ResourceRestEndpoints):
    """Adds the route that runs an action against an item"""

    def add_endpoints(self):
        super().add_endpoints()
        self.endpoints.append(
            Endpoint(
                url=f"{self.get_item_url()}/run",
                name="ai_action_run",
                func=self.run,
                methods=["POST"],
                # Configuring the actions and running them are separate rights: an editor runs them
                # without being trusted with the provider credentials behind them
                auth=[required_privilege_rule(AI_PRIVILEGE)],
                parent=self,
            )
        )

    async def run(self, request: Request) -> Response:
        action = await self._get_action(request)

        try:
            payload = RunActionPayload.model_validate(await request.get_json() or {})
        except ValidationError as error:
            raise SuperdeskApiError.badRequestError(
                message=gettext("Invalid payload"),
                payload=get_field_errors_from_pydantic_validation_error(error),
            )

        service = cast(AIActionsService, self.service)

        try:
            result = await service.run(action, payload)
        except AIProviderError as error:
            raise to_api_error(error)

        return Response(body=result, status_code=200)

    async def _get_action(self, request: Request) -> AIAction:
        item_id = request.get_view_args("item_id")
        action = await self.service.find_by_id(item_id) if item_id else None

        if action is None:
            raise SuperdeskApiError.notFoundError(
                gettext("AI action with ID '{action_id}' not found").format(action_id=item_id)
            )

        return cast(AIAction, action)
