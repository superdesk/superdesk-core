from typing import Any, List

from superdesk.core.resources import AsyncResourceService

from .models import AIAction, AIActionType, AIProvider


class AIProvidersService(AsyncResourceService[AIProvider]):
    async def on_update(self, updates: dict[str, Any], original: AIProvider) -> None:
        if updates.get("api_key") == "":
            # The key is excluded from every response, so a client editing a provider never has it
            # to send back. An empty key therefore means "keep the stored one", the same as leaving
            # the field out of the payload. An explicit ``null`` is the only way to clear it.
            updates.pop("api_key")

        await super().on_update(updates, original)


class AIActionsService(AsyncResourceService[AIAction]):
    """Service for the ``ai_actions`` resource.

    A summary has a single answer by definition, so ``suggestions_count`` is forced to 1 for that
    action type. It is forced here rather than in a model validator because only the fields present
    in the client's payload are written to the database on a PATCH, so a value a validator derived
    from another field would be validated and then dropped.
    """

    async def on_create(self, docs: List[AIAction]) -> None:
        for doc in docs:
            if doc.action_type == AIActionType.SUMMARY:
                doc.suggestions_count = 1

        await super().on_create(docs)

    async def on_update(self, updates: dict[str, Any], original: AIAction) -> None:
        action_type = updates.get("action_type", original.action_type)
        suggestions_count = updates.get("suggestions_count", original.suggestions_count)

        if action_type == AIActionType.SUMMARY and suggestions_count != 1:
            updates["suggestions_count"] = 1

        await super().on_update(updates, original)
