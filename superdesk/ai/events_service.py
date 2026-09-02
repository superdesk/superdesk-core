import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from quart_babel import gettext

from superdesk.core.resources import AsyncResourceService, fields
from superdesk.errors import SuperdeskApiError
from superdesk.utc import utcnow

from .errors import AIErrorKind
from .models import (
    SHORT_OUTPUT_ACTION_TYPES,
    AIAction,
    AIEvent,
    AIEventOutcome,
    AIEventSource,
    AIEventStatus,
    AIProvider,
)
from .providers.base import CompletionResult

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
        input_tokens=result.input_tokens if result is not None else None,
        output_tokens=result.output_tokens if result is not None else None,
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
