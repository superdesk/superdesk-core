import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List

from quart_babel import gettext

from superdesk.core import get_current_async_app
from superdesk.core.resources import AsyncResourceService, fields
from superdesk.errors import SuperdeskApiError
from superdesk.text_utils import get_text
from superdesk.utc import utcnow

from .errors import AIErrorKind, AIProviderError
from .models import (
    SHORT_OUTPUT_ACTION_TYPES,
    AIAction,
    AIActionType,
    AIEvent,
    AIEventOutcome,
    AIEventSource,
    AIEventStatus,
    AIProvider,
    RunActionPayload,
)
from .prompts import (
    SUPPORTED_ACTION_TYPES,
    parse_suggestions,
    render_system_prompt,
    render_user_message,
    unsupported_action_type,
)
from .providers import get_client
from .providers.base import CompletionMessage, CompletionRequest, CompletionResult

logger = logging.getLogger(__name__)


@dataclass
class AIRunRecord:
    """What one run of an AI action produced, for the run log.

    The record carries the action and the provider it was run with, the model asked for, the item
    identified by ``item_id``, ``content_profile`` and ``language``, the two timestamps, the size of
    the text sent and received, and either the provider result with the suggestions read out of it
    or the kind of failure. The article text itself is never part of it, only ``input_chars`` and
    ``output_chars``, so the log cannot become a second copy of the content of every item an action
    is run against.

    ``provider`` is the stored provider, credentials included, so anything writing this record out
    has to pick the fields it needs rather than serialise it whole.
    """

    action: AIAction
    provider: AIProvider
    item_id: str
    model_requested: str
    requested_at: datetime
    responded_at: datetime
    input_chars: int
    content_profile: str | None = None
    language: str | None = None
    user_id: str | None = None
    desk_id: str | None = None
    source: AIEventSource = AIEventSource.API
    result: CompletionResult | None = None
    suggestions: list[str] = field(default_factory=list)
    error_kind: AIErrorKind | None = None

    @property
    def latency_ms(self) -> int:
        return int((self.responded_at - self.requested_at).total_seconds() * 1000)

    @property
    def output_chars(self) -> int:
        return len(self.result.content) if self.result is not None else 0


def build_event(record: AIRunRecord) -> AIEvent:
    """Turn the record of one run into the ``ai_events`` entry for it

    Only the fields the log needs are taken from the provider: it holds the credentials the run was
    made with, and every holder of ``ai_studio`` can read the log.
    """

    result = record.result
    keeps_suggestions = record.action.action_type in SHORT_OUTPUT_ACTION_TYPES

    return AIEvent(
        # The ID is generated here rather than left to the field's default factory: the pydantic
        # mypy plugin runs with ``warn_required_dynamic_aliases``, which makes a field with alias
        # choices, as the resource ID has, a required argument of the constructor.
        id=fields.ObjectId(),
        item_id=record.item_id,
        action_id=record.action.id,
        action_type=record.action.action_type,
        provider_id=record.provider.id,
        provider_type=record.provider.provider_type,
        model_requested=record.model_requested,
        model_reported=result.model if result is not None else None,
        user_id=record.user_id,
        desk_id=record.desk_id,
        content_profile=record.content_profile,
        language=record.language,
        source=record.source,
        requested_at=record.requested_at,
        responded_at=record.responded_at,
        latency_ms=record.latency_ms,
        input_chars=record.input_chars,
        output_chars=record.output_chars,
        prompt_tokens=result.prompt_tokens if result is not None else None,
        completion_tokens=result.completion_tokens if result is not None else None,
        status=AIEventStatus.ERROR if record.error_kind is not None else AIEventStatus.OK,
        error_kind=record.error_kind,
        suggestions=list(record.suggestions) if keeps_suggestions else [],
    )


async def record_run(record: AIRunRecord) -> str | None:
    """Store the log entry for one run of an AI action and return its ID

    Never raises. It is awaited on the success path, where a failure would turn a good run into a
    500, and while a provider failure is being handled, where it would hide the error the client
    has to be told about. A run that could not be logged is answered with no event ID.
    """

    try:
        event = build_event(record)
        await AIEventsService().create([event])
    except Exception:
        logger.exception("Failed to write the ai_events entry of an AI action run")
        return None

    return str(event.id)


class AIEventsService(AsyncResourceService[AIEvent]):
    """Service for the ``ai_events`` resource.

    Entries are written by the run flow and are a record of what happened, so nothing about the run
    itself can be edited afterwards. The only update a client can make is reporting what was done
    with the answers, which is what ``outcome`` and ``applied_index`` are for.
    """

    #: Fields a client may send in an update, every other one is rejected
    OUTCOME_FIELDS = frozenset({"outcome", "applied_index"})

    #: Outcomes that mean one of the answers was used, so ``applied_index`` can name which. A tuple
    #: rather than a set: membership then compares with ``==``, which matches the plain string of a
    #: payload against the enum member, where a set would compare hashes and never match.
    APPLIED_OUTCOMES = (AIEventOutcome.ACCEPTED, AIEventOutcome.EDITED)

    async def on_update(self, updates: dict[str, Any], original: AIEvent) -> None:
        rejected = sorted(set(updates) - self.OUTCOME_FIELDS)
        if rejected:
            raise SuperdeskApiError.badRequestError(
                gettext("Only the outcome of an AI event can be updated, not: {fields}").format(
                    fields=", ".join(rejected)
                )
            )

        self._validate_outcome(updates, original)

        # Stamped by the server so the delay between a run and the decision about it can be
        # measured from entries a client cannot backdate
        updates["outcome_at"] = utcnow()

        await super().on_update(updates, original)

    def _validate_outcome(self, updates: dict[str, Any], original: AIEvent) -> None:
        """Check a report against the answers the run it is about produced

        An outcome can be reported more than once, an accepted suggestion that is later edited for
        instance, but never back to ``pending``: that is the state of an event nobody has decided
        about yet, so reporting it would erase a decision rather than record one.

        An outcome that means no answer was used clears ``applied_index``, so an index an earlier
        report left behind cannot outlive the outcome it belonged to.

        :raises SuperdeskApiError: If the report says nothing was decided, carries an index while
            saying no answer was used, or names a suggestion the run did not produce
        """

        outcome = updates.get("outcome", original.outcome)
        if isinstance(outcome, AIEventOutcome):
            outcome = outcome.value

        if outcome == AIEventOutcome.PENDING:
            raise SuperdeskApiError.badRequestError(
                gettext("'pending' is the state of an AI event before its outcome is known, not an outcome to report")
            )

        applied_index = updates.get("applied_index")

        if outcome not in self.APPLIED_OUTCOMES:
            if applied_index is not None:
                raise SuperdeskApiError.badRequestError(
                    gettext(
                        "'applied_index' belongs to an outcome of 'accepted' or 'edited', not to '{outcome}'"
                    ).format(outcome=outcome)
                )

            updates["applied_index"] = None
            return

        if applied_index is None:
            return

        # ``True`` is an ``int`` in Python and would otherwise pass as the index of the first answer
        if not isinstance(applied_index, int) or isinstance(applied_index, bool):
            raise SuperdeskApiError.badRequestError(
                gettext("'applied_index' must be the position of a suggestion, not '{value}'").format(
                    value=applied_index
                )
            )

        if not 0 <= applied_index < len(original.suggestions):
            raise SuperdeskApiError.badRequestError(
                gettext("'applied_index' {index} names none of the {count} suggestions of this AI event").format(
                    index=applied_index, count=len(original.suggestions)
                )
            )


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
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
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
