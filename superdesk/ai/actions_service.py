from typing import Any, List

from quart_babel import gettext

from superdesk.core import get_current_async_app
from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError
from superdesk.text_utils import get_text
from superdesk.utc import utcnow

from .errors import AIErrorKind, AIProviderError
from .events_service import AIRunRecord, record_run
from .models import AIAction, AIActionType, AIProvider, RunActionPayload
from .prompts import (
    SUPPORTED_ACTION_TYPES,
    parse_suggestions,
    render_system_prompt,
    render_user_message,
    unsupported_action_type,
)
from .providers import get_client
from .providers.base import CompletionMessage, CompletionRequest, CompletionResult
from .providers_service import AIProvidersService


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

    async def run(self, action: AIAction, payload: RunActionPayload, user_id: str | None = None) -> dict[str, Any]:
        """Run an action against one item and return the suggestions it produced

        :param action: The action to run
        :param payload: The item to run it against, with the text the client currently holds
        :param user_id: ID of the user the run is made for, stored on the event
        :raises SuperdeskApiError: If the action, the item or the provider cannot be used as asked
        :raises AIProviderError: If the provider does not produce a usable answer
        """

        if not action.active:
            raise SuperdeskApiError.badRequestError(
                gettext("AI action '{name}' is not active").format(name=action.name)
            )
        if action.action_type not in SUPPORTED_ACTION_TYPES:
            raise unsupported_action_type(action.action_type)

        item = await self._get_item(payload.item_id)
        self._check_content_profile(action, item)
        texts = self._get_input_texts(action, payload, item)

        provider = await self._get_provider(action)
        model = action.model or provider.default_model
        if not model:
            raise SuperdeskApiError.badRequestError(
                gettext("AI action '{name}' has no model and its provider has no default one").format(name=action.name)
            )

        language = payload.language or item.get("language")
        request = CompletionRequest(
            model=model,
            messages=[
                CompletionMessage(
                    role="system",
                    content=render_system_prompt(
                        action.action_type,
                        output_field=action.output_field,
                        count=action.suggestions_count,
                        max_characters=action.max_characters,
                        language=language,
                        system_prompt=action.parameters.system_prompt,
                    ),
                ),
                CompletionMessage(role="user", content=render_user_message(texts)),
            ],
            temperature=action.parameters.temperature,
            json_mode=True,
        )

        record = AIRunRecord(
            action=action,
            provider=provider,
            item_id=payload.item_id,
            content_profile=item.get("profile"),
            model_requested=model,
            requested_at=utcnow(),
            responded_at=utcnow(),
            input_chars=sum(len(text) for text in texts.values()),
            language=language,
            user_id=user_id,
            desk_id=self._get_desk_id(item),
            source=payload.source,
        )

        try:
            result = await get_client(provider).complete(request)
        except AIProviderError as error:
            record.responded_at = utcnow()
            record.error_kind = error.kind
            await record_run(record)
            raise

        record.responded_at = utcnow()
        record.result = result

        try:
            answers = self._read_suggestions(action, result)
        except AIProviderError as error:
            record.error_kind = error.kind
            await record_run(record)
            raise

        suggestions = [
            {
                "text": text,
                # An answer that is too long is reported in full rather than cut, so the client can
                # show the editor what the provider wrote and let them shorten it
                "over_limit": action.max_characters is not None and len(text) > action.max_characters,
            }
            for text in answers
        ]
        record.suggestions = [str(suggestion["text"]) for suggestion in suggestions]

        return {
            "suggestions": suggestions,
            "event_id": await record_run(record),
            "provider": str(provider.id),
            "model": result.model,
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        }

    def _read_suggestions(self, action: AIAction, result: CompletionResult) -> list[str]:
        """Read the answers out of a completion

        :raises AIProviderError: If the completion carries no text at all, so that a run which
            produced nothing is reported as a provider failure and not as a run with no answers
        """

        if not result.content.strip():
            raise AIProviderError(
                AIErrorKind.INVALID_RESPONSE,
                gettext("The AI provider answered with an empty completion"),
            )

        return parse_suggestions(result.content, action.suggestions_count)

    async def _get_item(self, item_id: str) -> dict[str, Any]:
        """Load the item as stored, without validating it against the archive model.

        An action names the fields it reads by name, including the custom fields a content profile
        adds, which the model does not declare.
        """

        archive_service = get_current_async_app().resources.get_resource_service("archive")
        item = await archive_service.find_by_id_raw(item_id)

        if item is None:
            raise SuperdeskApiError.notFoundError(gettext("Item with ID '{item_id}' not found").format(item_id=item_id))

        return item

    def _get_desk_id(self, item: dict[str, Any]) -> str | None:
        """ID of the desk the item sits on, ``None`` for an item that is not on one"""

        task = item.get("task")
        desk_id = task.get("desk") if isinstance(task, dict) else None

        return str(desk_id) if desk_id else None

    def _check_content_profile(self, action: AIAction, item: dict[str, Any]) -> None:
        if action.content_profiles and item.get("profile") not in action.content_profiles:
            raise SuperdeskApiError.badRequestError(
                gettext("AI action '{name}' is not available for the content profile of this item").format(
                    name=action.name
                )
            )

    def _get_input_texts(self, action: AIAction, payload: RunActionPayload, item: dict[str, Any]) -> dict[str, str]:
        """Collect the text of every input field, preferring what the client sent over the item"""

        provided = payload.fields or {}
        texts: dict[str, str] = {}

        for name in action.input_fields:
            value = provided.get(name, item.get(name))
            if not isinstance(value, str):
                continue

            text = get_text(value, content="html", lf_on_block=True).strip()
            if text:
                texts[name] = text

        if not texts:
            raise SuperdeskApiError.badRequestError(
                gettext("The item has no text in the fields the action reads: {fields}").format(
                    fields=", ".join(action.input_fields)
                )
            )

        return texts

    async def _get_provider(self, action: AIAction) -> AIProvider:
        provider = await AIProvidersService().find_by_id(action.provider)

        if provider is None:
            raise SuperdeskApiError.badRequestError(
                gettext("The provider of AI action '{name}' no longer exists").format(name=action.name)
            )
        if not provider.active:
            raise SuperdeskApiError.badRequestError(
                gettext("AI provider '{name}' is not active").format(name=provider.name)
            )

        return provider
