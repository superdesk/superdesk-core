from typing import Any

from quart_babel import gettext

from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError

from .models import AIProvider


class AIProvidersService(AsyncResourceService[AIProvider]):
    """Service for the ``ai_providers`` resource.

    ``available_models`` is the shortlist an AI action picks its model from, so a model cannot be
    dropped from it while an action still names that model. ``default_model`` is outside that
    shortlist by design: it is what an action naming no model falls back to, and it may point at a
    model the actions themselves are not allowed to pick.
    """

    async def on_update(self, updates: dict[str, Any], original: AIProvider) -> None:
        if updates.get("api_key") == "":
            # The key is excluded from every response, so a client editing a provider never has it
            # to send back. An empty key therefore means "keep the stored one", the same as leaving
            # the field out of the payload. An explicit ``null`` is the only way to clear it.
            updates.pop("api_key")

        await super().on_update(updates, original)

    async def validate_update(self, updates: dict[str, Any], original: AIProvider, etag: str | None) -> dict[str, Any]:
        updated = await super().validate_update(updates, original, etag)

        await self._check_models_in_use(original, updated.get("available_models") or [])

        return updated

    async def _check_models_in_use(self, original: AIProvider, available_models: list[str]) -> None:
        """Refuse to narrow the shortlist past a model an action of this provider still names

        :raises SuperdeskApiError: If an action would be left naming a model outside the shortlist
        """

        if not available_models:
            # An empty shortlist allows every model, so no action can fall outside it
            return

        dropped = sorted(set(original.available_models) - set(available_models))
        if not dropped:
            return

        # Imported here because ``actions_service`` imports this module
        from .actions_service import AIActionsService

        cursor = await AIActionsService().find(
            {"provider": original.id, "model": {"$in": dropped}},
            max_results=100,
            use_mongo=True,
        )
        actions = await cursor.to_list()

        if not actions:
            return

        raise SuperdeskApiError.badRequestError(
            gettext("'available_models' cannot drop {models}, still used by AI actions: {actions}").format(
                models=", ".join(sorted({action.model for action in actions if action.model})),
                actions=", ".join(sorted(action.name for action in actions)),
            )
        )
