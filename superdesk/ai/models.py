import enum
from typing import Annotated, Any

from pydantic import AfterValidator, AnyHttpUrl, BeforeValidator, Field, TypeAdapter
from pydantic_core import PydanticCustomError
from quart_babel import gettext

from superdesk.core.resources import BaseModel, Dataclass, ResourceModelWithObjectId, dataclass, fields
from superdesk.core.resources.validators import (
    validate_data_relation_async,
    validate_maxlength,
    validate_minlength,
    validate_not_empty,
)

from .errors import AIErrorKind
from .providers import allowed_provider_types

_http_url_adapter: TypeAdapter = TypeAdapter(AnyHttpUrl)

# Validates as an HTTP(S) URL and stores it without a trailing slash. Provider clients append
# their paths with a leading slash, so a stored trailing slash would produce a double slash in
# every request URL. Kept a plain ``str`` so it stays serializable for MongoDB storage.
BaseUrlStr = Annotated[str, BeforeValidator(lambda value: str(_http_url_adapter.validate_python(value)).rstrip("/"))]


def validate_provider_type() -> AfterValidator:
    """Validates that the value is the name of a registered AI provider type"""

    def _validate_provider_type(value: str) -> str:
        if value not in allowed_provider_types:
            raise PydanticCustomError(
                "provider_type",
                gettext("Unknown AI provider type '{provider_type}'"),
                {"provider_type": value},
            )

        return value

    return AfterValidator(_validate_provider_type)


class AIProvider(ResourceModelWithObjectId):
    name: Annotated[str, validate_not_empty()]
    provider_type: Annotated[str, validate_provider_type()]
    base_url: BaseUrlStr
    api_key: str | None = None
    default_model: str | None = None
    is_default: bool = False
    active: bool = True

    #: Type specific extras, such as the headers a gateway requires
    config: dict[str, Any] = Field(default_factory=dict)
    label: str | None = None


class AIActionType(str, enum.Enum):
    SUGGESTION = "suggestion"
    SUMMARY = "summary"
    REWRITE = "rewrite"
    TRANSLATION = "translation"


#: Action types whose answers are a headline or a paragraph, short enough to keep on the run log
#: next to the outcome a client reports later. A rewrite or a translation answers with the whole
#: article, so storing its answers would make the log a second copy of the content.
SHORT_OUTPUT_ACTION_TYPES = frozenset({AIActionType.SUGGESTION, AIActionType.SUMMARY})


@dataclass
class AIActionParameters(Dataclass):
    temperature: float = 0.7

    #: Replaces the system prompt built from the action type, leaving the instructions that carry
    #: the answer format in place
    system_prompt: str | None = None


class AIAction(ResourceModelWithObjectId):
    name: Annotated[str, validate_not_empty()]
    action_type: AIActionType
    active: bool = True

    #: Names of the item fields whose text is sent to the provider
    input_fields: Annotated[list[str], validate_minlength(1)]

    #: Name of the item field the suggestions are written back to by the client
    output_field: Annotated[str, validate_not_empty()]

    max_characters: int | None = None
    suggestions_count: Annotated[int, validate_minlength(1), validate_maxlength(10)] = 3

    #: Content profiles the action is offered for, an empty list means every profile
    content_profiles: list[str] = Field(default_factory=list)

    provider: Annotated[fields.ObjectId, validate_data_relation_async("ai_providers")]

    #: Model to run the action with, falls back to the provider's ``default_model``
    model: str | None = None

    parameters: AIActionParameters = Field(default_factory=AIActionParameters)


class AIEventSource(str, enum.Enum):
    """Where a run was started from, so editor use can be told apart from integrations"""

    AUTHORING = "authoring"
    API = "api"


class AIEventStatus(str, enum.Enum):
    OK = "ok"
    ERROR = "error"


class AIEventOutcome(str, enum.Enum):
    """What was done with the answers of a run, reported by the client after the fact"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    DISCARDED = "discarded"


class AIEvent(ResourceModelWithObjectId):
    """One run of an AI action, written whether the run succeeded or failed.

    The article text is never part of an event, only ``input_chars`` and ``output_chars``. An entry
    is written per run, so holding the text would make the log a copy of the content of every item
    an action is run against.

    ``user_id`` and ``desk_id`` are stored as text: they are copied from a session and from an item
    rather than taken from a validated model, so the type they are stored with elsewhere is not
    guaranteed. The action and provider ids keep the type they have on their own resources.
    """

    item_id: str
    action_id: fields.ObjectId
    action_type: AIActionType
    provider_id: fields.ObjectId
    provider_type: str
    model_requested: str

    #: Model the provider answered with, which can be a dated snapshot of the one asked for
    model_reported: str | None = None

    user_id: str | None = None
    desk_id: str | None = None
    content_profile: str | None = None
    language: str | None = None
    source: AIEventSource = AIEventSource.API

    requested_at: fields.UTCDatetime
    responded_at: fields.UTCDatetime
    latency_ms: int
    input_chars: int
    output_chars: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    status: AIEventStatus
    error_kind: AIErrorKind | None = None

    #: Answers of the run, kept for the types listed in ``SHORT_OUTPUT_ACTION_TYPES`` only
    suggestions: list[str] = Field(default_factory=list)

    outcome: AIEventOutcome = AIEventOutcome.PENDING
    applied_index: int | None = None
    outcome_at: fields.UTCDatetime | None = None


class RunActionPayload(BaseModel):
    """Body of a request to run an AI action against one item"""

    item_id: Annotated[str, validate_not_empty()]

    #: Text of the input fields as the client currently has them, used instead of the stored item.
    #: The editor the run is started from usually holds changes that were never saved.
    fields: dict[str, str] | None = None

    #: Language to answer in, falls back to the language of the item
    language: str | None = None

    #: Where the run was started from, kept on the event the run writes
    source: AIEventSource = AIEventSource.API
