import logging
from typing import Any, List

from quart_babel import gettext

from superdesk.content_types_async import ContentTypesService
from superdesk.core import get_current_async_app
from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError
from superdesk.text_utils import get_text
from superdesk.users.services import get_invisible_stages_async
from superdesk.utc import utcnow
from superdesk.vocabularies_async.service import VocabulariesService

from .errors import AIErrorKind, AIProviderError
from .events_service import AIRunRecord, record_run
from .models import (
    BUILT_IN_TEXT_FIELDS,
    EXTRA_INSTRUCTIONS_MAX_LENGTH,
    SINGLE_ANSWER_ACTION_TYPES,
    AIAction,
    AIProvider,
    RunActionPayload,
)
from .prompts import (
    PLAIN_TEXT_ACTION_TYPES,
    SUPPORTED_ACTION_TYPES,
    parse_suggestions,
    render_system_prompt,
    render_user_message,
    unsupported_action_type,
)
from .providers import get_client
from .providers.base import CompletionMessage, CompletionRequest, CompletionResult
from .providers_service import AIProvidersService

logger = logging.getLogger(__name__)


class AIActionsService(AsyncResourceService[AIAction]):
    """Service for the ``ai_actions`` resource.

    A summary has a single answer by definition, so ``suggestions_count`` is forced to 1 for the
    types in ``SINGLE_ANSWER_ACTION_TYPES``. It is forced here rather than in a model validator
    because only the fields present in the client's payload are written to the database on a PATCH,
    so a value a validator derived from another field would be validated and then dropped.

    Some rules apply to what a request sets and not to what is stored, see ``_check_request``.
    """

    async def on_create(self, docs: List[AIAction]) -> None:
        for doc in docs:
            if doc.action_type in SINGLE_ANSWER_ACTION_TYPES:
                doc.parameters.suggestions_count = 1

        await super().on_create(docs)

    async def on_update(self, updates: dict[str, Any], original: AIAction) -> None:
        # Before the merge: it copies the stored parameters, legacy keys included, into the updates
        await self._check_request(updates, original)

        self._merge_parameters(updates, original)

        action_type = updates.get("action_type", original.action_type)
        # A value of the wrong type may not be hashable, and is left for the model to report, as are
        # parameters that are not an object
        if (
            isinstance(action_type, str)
            and action_type in SINGLE_ANSWER_ACTION_TYPES
            and isinstance(updates.get("parameters", {}), dict)
        ):
            parameters = updates.setdefault("parameters", original.parameters.to_dict())
            parameters["suggestions_count"] = 1

        await super().on_update(updates, original)

    async def validate_create(self, doc: AIAction) -> None:
        await super().validate_create(doc)

        await self._check_request(doc.to_dict())
        await self._check_model_available(doc.provider, doc.model)

    async def _check_request(self, fields: dict[str, Any], original: AIAction | None = None) -> None:
        """Check what a create or an update sets, leaving out everything it does not set

        These rules are not on the model because a stored action is validated again every time it is
        loaded. An action saved before a rule existed, or naming a custom field that has since been
        removed, has to keep loading, listing and running. An update that does not touch the
        offending value has to go through too, including one that sends the stored value back
        unchanged, as a form saving the whole action does.

        Errors are reported per field like the model's own, with the parameters nested under
        ``parameters``. Values of the wrong type are left for the model to report.

        :param fields: The fields of the action the request sets, as the client sent them
        :param original: The stored action an update applies to, ``None`` on create
        :raises SuperdeskApiError: If the request sets a value it may not
        """

        issues: dict[str, Any] = {}

        # The model allows unknown keys. A dotted one would reach MongoDB's ``$set`` as a path into a
        # field, writing a parameter or a list entry past every check here and in the model.
        for key in fields:
            if "." in key or key.startswith("$"):
                issues[key] = {"field_name": gettext("Not a field of an AI action")}

        parameters = fields.get("parameters")
        if isinstance(parameters, dict):
            stored_parameters = original.parameters.to_dict() if original is not None else {}
            parameter_issues = self._check_parameters(parameters, stored_parameters)
            if parameter_issues:
                issues["parameters"] = parameter_issues

        stored_inputs = set(original.input_fields) if original is not None else set()
        stored_output = original.output_field if original is not None else None

        input_fields = fields.get("input_fields")
        input_names = (
            [name.strip() for name in input_fields if isinstance(name, str) and name.strip() not in stored_inputs]
            if isinstance(input_fields, list)
            else []
        )
        output_field = fields.get("output_field")
        output_names = (
            [output_field.strip()]
            if isinstance(output_field, str) and output_field.strip() and output_field.strip() != stored_output
            else []
        )

        text_fields = await self._find_text_fields(input_names + output_names)
        for field, names in (("input_fields", input_names), ("output_field", output_names)):
            unknown = [name for name in names if name not in text_fields]
            if unknown:
                issues[field] = {
                    "text_field": gettext("Not a built-in or custom text field: {fields}").format(
                        fields=", ".join(unknown)
                    )
                }

        if issues:
            raise SuperdeskApiError.badRequestError(message=gettext("Invalid AI action"), payload=issues)

    def _check_parameters(self, parameters: dict[str, Any], stored: dict[str, Any]) -> dict[str, Any]:
        issues: dict[str, Any] = {}

        extra_instructions = parameters.get("extra_instructions")
        if (
            isinstance(extra_instructions, str)
            and len(extra_instructions.strip()) > EXTRA_INSTRUCTIONS_MAX_LENGTH
            and extra_instructions.strip() != stored.get("extra_instructions")
        ):
            issues["extra_instructions"] = {
                "maxlength": gettext("At most {max_length} characters").format(max_length=EXTRA_INSTRUCTIONS_MAX_LENGTH)
            }

        return issues

    async def _find_text_fields(self, names: list[str]) -> set[str]:
        """Those of the names that are a built-in text field or the ID of a custom text field

        Custom fields are vocabularies with a ``field_type``, and only those of type ``text`` hold
        prose. They are read from the database as stored, so a vocabulary that does not pass the
        vocabulary model cannot fail the check. A deleted vocabulary is only marked ``_deleted``.
        """

        found = {name for name in names if name in BUILT_IN_TEXT_FIELDS}
        custom = list(set(names) - found)

        if custom:
            cursor = VocabulariesService().mongo_async.find(
                {"_id": {"$in": custom}, "field_type": "text", "_deleted": {"$ne": True}}, projection={"_id": 1}
            )
            found.update([vocabulary["_id"] async for vocabulary in cursor])

        return found

    async def validate_update(self, updates: dict[str, Any], original: AIAction, etag: str | None) -> dict[str, Any]:
        updated = await super().validate_update(updates, original, etag)

        await self._check_model_available(updated["provider"], updated.get("model"))

        return updated

    async def _check_model_available(self, provider_id: Any, model: str | None) -> None:
        """Check the model against the shortlist its provider restricts actions to

        :raises SuperdeskApiError: If the provider has a shortlist that does not hold the model
        """

        if model is None:
            return

        provider = await AIProvidersService().find_by_id(provider_id)

        # A provider that does not exist is reported by the relation validator on the field
        if provider is None or not provider.available_models:
            return

        if model not in provider.available_models:
            raise SuperdeskApiError.badRequestError(
                gettext("'model' '{model}' is not one of the provider's 'available_models': {models}").format(
                    model=model, models=", ".join(provider.available_models)
                )
            )

    def _merge_parameters(self, updates: dict[str, Any], original: AIAction) -> None:
        """Apply a partial ``parameters`` payload onto the stored ones

        A nested value is written whole, so a client sending one parameter would otherwise reset
        every other one to its default. Merging keeps patching a parameter meaning what patching a
        field of the action means, with an explicit ``null`` still clearing.
        """

        parameters = updates.get("parameters")
        if not isinstance(parameters, dict):
            return

        updates["parameters"] = {**original.parameters.to_dict(), **parameters}

    async def run(self, action: AIAction, payload: RunActionPayload, user_id: str | None = None) -> dict[str, Any]:
        """Run an action against one item and return the suggestions it produced

        :param action: The action to run
        :param payload: The item to run it against, with the text the client currently holds
        :param user_id: ID of the user the run is made for, stored on the event. The item has to be
            one this user can read. ``None`` only for a run made by the system itself.
        :raises SuperdeskApiError: If the action, the item or the provider cannot be used as asked
        :raises AIProviderError: If the provider does not produce a usable answer
        """

        if not action.active:
            raise SuperdeskApiError.badRequestError(
                gettext("AI action '{name}' is not active").format(name=action.name)
            )
        if action.action_type not in SUPPORTED_ACTION_TYPES:
            raise unsupported_action_type(action.action_type)

        item = await self.get_item(payload.item_id, user_id)
        self._check_content_profile(action, item)
        texts = self._get_input_texts(action, payload, item)

        provider = await self._get_provider(action)
        model = action.model or provider.default_model
        if not model:
            raise SuperdeskApiError.badRequestError(
                gettext("AI action '{name}' has no model and its provider has no default one").format(name=action.name)
            )

        language = payload.language or item.get("language")
        max_characters = await self._get_max_characters(action, item)
        request = CompletionRequest(
            model=model,
            messages=[
                CompletionMessage(
                    role="system",
                    content=render_system_prompt(
                        action.action_type,
                        output_field=action.output_field,
                        count=action.parameters.suggestions_count,
                        max_characters=max_characters,
                        language=language,
                        extra_instructions=action.parameters.extra_instructions,
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
                "over_limit": max_characters is not None and len(text) > max_characters,
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

        return parse_suggestions(
            result.content,
            action.parameters.suggestions_count,
            plain_text=action.action_type in PLAIN_TEXT_ACTION_TYPES,
        )

    async def _get_max_characters(self, action: AIAction, item: dict[str, Any]) -> int | None:
        """How long an answer may be, from the action or from the content profile of the item

        The profile is the length the field can actually store, so it is the default and
        ``parameters.max_characters`` overrides it. ``None`` when neither names one.
        """

        if action.parameters.max_characters is not None:
            return action.parameters.max_characters

        try:
            schema = await ContentTypesService().get_schema(item)
        except Exception:
            # Broad on purpose: the length is an enrichment, so nothing about reading the profile,
            # from an item that has none to an unreachable database, should fail the run.
            logger.exception("Failed to read the content profile of an item an AI action was run against")
            return None

        # A field with no maxlength, or one carrying something other than a number, means no limit
        try:
            return int((schema or {})[action.output_field]["maxlength"])
        except (KeyError, TypeError, ValueError):
            return None

    async def get_item(self, item_id: str, user_id: str | None) -> dict[str, Any]:
        """Load the item as stored, without validating it against the archive model.

        An action names the fields it reads by name, including the custom fields a content profile
        adds, which the model does not declare.

        :param item_id: ID of the item in ``archive``
        :param user_id: ID of the user who has to be able to read the item, ``None`` to skip the check
        :raises SuperdeskApiError: If the item does not exist, or the user cannot read it
        """

        archive_service = get_current_async_app().resources.get_resource_service("archive")
        item = await archive_service.find_by_id_raw(item_id)

        if item is None:
            raise SuperdeskApiError.notFoundError(gettext("Item with ID '{item_id}' not found").format(item_id=item_id))

        if user_id is not None:
            await self._check_item_readable(item, user_id)

        return item

    async def _check_item_readable(self, item: dict[str, Any], user_id: str) -> None:
        """Refuse an item the user could not open in Superdesk

        The answers are written from the text of the item, so a run must not reach an item its user
        cannot read. Two rules of ``archive`` apply: an item in a stage that is hidden from the user
        (what ``GET /archive/<id>`` refuses), and an item in the personal space of another user
        (what listings and editing refuse). An item with no desk belongs to the user it is assigned
        to or, when it is assigned to nobody, to the users who created and last changed it, as in
        the search filter of ``archive``.

        :raises SuperdeskApiError: If the user cannot read the item
        """

        task = item.get("task")
        task = task if isinstance(task, dict) else {}

        in_other_personal_space = False
        if not task.get("desk"):
            owner = task.get("user")
            candidates = [owner] if owner else [item.get("original_creator"), item.get("version_creator")]
            owners = {str(candidate) for candidate in candidates if candidate}
            in_other_personal_space = bool(owners) and user_id not in owners

        stage = task.get("stage")
        in_hidden_stage = bool(stage) and str(stage) in {
            str(hidden["_id"]) for hidden in await get_invisible_stages_async(user_id)
        }

        if in_other_personal_space or in_hidden_stage:
            raise SuperdeskApiError.forbiddenError(message=gettext("You do not have permission to read this item"))

    def _get_desk_id(self, item: dict[str, Any]) -> str | None:
        """ID of the desk the item sits on, ``None`` for an item that is not on one"""

        task = item.get("task")
        desk_id = task.get("desk") if isinstance(task, dict) else None

        return str(desk_id) if desk_id else None

    async def find_available(self, item: dict[str, Any]) -> list[AIAction]:
        """Actions that can be run against the item, sorted by name

        Leaves out every action a run would refuse before calling the provider: an inactive action
        or provider, an action type with no prompt yet, an action limited to other content profiles,
        and an action with no model to run with.
        """

        actions = [action async for action in self.get_all({"active": True})]
        provider_ids = list({action.provider for action in actions})
        providers = {
            provider.id: provider
            async for provider in AIProvidersService().get_all({"_id": {"$in": provider_ids}, "active": True})
        }

        available = []
        for action in actions:
            provider = providers.get(action.provider)
            if (
                provider is not None
                and action.action_type in SUPPORTED_ACTION_TYPES
                and self._is_offered_for(action, item)
                and (action.model or provider.default_model)
            ):
                available.append(action)

        return sorted(available, key=lambda action: action.name.lower())

    def _is_offered_for(self, action: AIAction, item: dict[str, Any]) -> bool:
        return not action.content_profiles or item.get("profile") in action.content_profiles

    def _check_content_profile(self, action: AIAction, item: dict[str, Any]) -> None:
        if not self._is_offered_for(action, item):
            raise SuperdeskApiError.badRequestError(
                gettext("AI action '{name}' is not available for the content profile of this item").format(
                    name=action.name
                )
            )

    def _get_input_texts(self, action: AIAction, payload: RunActionPayload, item: dict[str, Any]) -> dict[str, str]:
        """Collect the text of every input field, preferring what the client sent over the item

        A built-in field is read from the top level of the item, any other name from ``extra``, where
        custom fields are stored. A custom field can share its ID with a top-level key of the item
        (``source``, for one), which holds something else. Other names fall back to the top level,
        so an action stored before the field names were checked keeps reading what it used to.
        """

        provided = payload.fields or {}
        extra = item.get("extra")
        extra = extra if isinstance(extra, dict) else {}
        texts: dict[str, str] = {}

        for name in action.input_fields:
            if name in BUILT_IN_TEXT_FIELDS:
                stored = item.get(name)
            else:
                stored = extra.get(name)
                if not isinstance(stored, str):
                    stored = item.get(name)

            value = provided.get(name, stored)
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
