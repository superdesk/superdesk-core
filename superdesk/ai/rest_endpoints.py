from typing import cast

from pydantic import ValidationError
from quart_babel import gettext

from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.resources import ResourceRestEndpoints
from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error
from superdesk.core.types import Request, Response
from superdesk.core.web import Endpoint, ItemRequestViewArgs
from superdesk.errors import SuperdeskApiError
from superdesk.users.async_service import get_privileges, is_admin

from .actions_service import AIActionsService
from .errors import AIProviderError, to_api_error
from .models import AIAction, AIEvent, AIProvider, RunActionPayload
from .privileges import AI_PRIVILEGE, AI_STUDIO_PRIVILEGE
from .providers import get_client


def get_request_user_id(request: Request) -> str | None:
    """ID of the authenticated user as text, for the run log"""

    user = request.user
    user_id = user.get("_id") if isinstance(user, dict) else None

    return str(user_id) if user_id else None


def request_user_has_privilege(request: Request, privilege: str) -> bool:
    """Whether the authenticated user holds a privilege, an administrator holding every one

    Same resolution as ``required_privilege_rule``, but as an answer rather than as a rejection, for
    checks that depend on which item is being touched and so cannot be made before the route runs.
    """

    user = request.user
    if not isinstance(user, dict):
        return False
    if is_admin(user):
        return True

    return bool(get_privileges(user, request.storage.request.get("role")).get(privilege))


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
            payload = RunActionPayload.from_dict(await request.get_json() or {})
        except ValidationError as error:
            raise SuperdeskApiError.badRequestError(
                message=gettext("Invalid payload"),
                payload=get_field_errors_from_pydantic_validation_error(error),
            )

        service = cast(AIActionsService, self.service)

        try:
            result = await service.run(action, payload, user_id=get_request_user_id(request))
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


class AIEventsEndpoints(ResourceRestEndpoints):
    """Restricts an outcome report to the run it is about and answers with the outcome alone"""

    #: The whole body of the answer to an outcome report. The client reporting holds ``ai``, which
    #: is not enough to read an event, so the answer to its own update must not hand it one.
    RESPONSE_FIELDS = ("_id", "outcome", "applied_index", "outcome_at")

    async def update_item(self, args: ItemRequestViewArgs, params: None, request: Request) -> Response:
        """Report what was done with the answers of one run

        Ownership is checked here rather than in ``AIEventsService.on_update`` because it depends on
        who is asking, which the service hooks are not given.
        """

        await self._check_report_allowed(args.item_id, request)
        response = await super().update_item(args, params, request)

        if response.status_code != 200:
            return response

        updated = cast(dict, response.body)

        return Response(
            {field: updated.get(field) for field in self.RESPONSE_FIELDS},
            response.status_code,
            response.headers,
        )

    async def _check_report_allowed(self, item_id: str, request: Request) -> None:
        """Reject a report about a run that was made for somebody else

        Holders of ``ai_studio`` are exempt: the whole log is readable to them already, so being
        able to report on any entry of it grants nothing they do not have.
        """

        if request_user_has_privilege(request, AI_STUDIO_PRIVILEGE):
            return

        event = await self.service.find_by_id(item_id)
        if event is None:
            # Answering the 404 is left to the base handler, which looks the event up again
            return

        user_id = get_request_user_id(request)
        if user_id is None or user_id != cast(AIEvent, event).user_id:
            raise SuperdeskApiError.forbiddenError(
                message=gettext("Only the user an AI action was run for can report what was done with its answers")
            )
