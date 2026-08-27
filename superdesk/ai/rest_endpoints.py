from quart_babel import gettext

from superdesk.core.resources import ResourceRestEndpoints
from superdesk.core.types import Request, Response
from superdesk.core.web import Endpoint
from superdesk.errors import SuperdeskApiError

from .errors import AIProviderError, to_api_error
from .models import AIProvider
from .providers import get_client


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
