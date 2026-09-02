from typing import Any

from quart_babel import gettext

from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError

from .models import AIProvider


class AIProvidersService(AsyncResourceService[AIProvider]):
    """Service for the ``ai_providers`` resource.

    ``default_model`` has to be one of ``available_models`` whenever the shortlist is not empty.
    The two fields can be changed independently, so the check is made against the state the write
    leaves behind rather than against what the payload carries.
    """

    async def validate_create(self, doc: AIProvider) -> None:
        self._check_default_model(doc.default_model, doc.available_models)

        await super().validate_create(doc)

    async def on_update(self, updates: dict[str, Any], original: AIProvider) -> None:
        if updates.get("api_key") == "":
            # The key is excluded from every response, so a client editing a provider never has it
            # to send back. An empty key therefore means "keep the stored one", the same as leaving
            # the field out of the payload. An explicit ``null`` is the only way to clear it.
            updates.pop("api_key")

        self._check_default_model(
            updates.get("default_model", original.default_model),
            updates.get("available_models", original.available_models),
        )

        await super().on_update(updates, original)

    def _check_default_model(self, default_model: Any, available_models: Any) -> None:
        """Check the default model against the shortlist the provider restricts itself to

        On an update both values come straight from the client's payload, which is only validated
        against the model afterwards, so either can still be of any shape. A value of the wrong
        shape is left to that validation, which answers with the field that is malformed, instead
        of being compared here against a value it cannot be compared to.

        :raises SuperdeskApiError: If the shortlist is not empty and does not hold the default model
        """

        if default_model is not None and not isinstance(default_model, str):
            return

        if not isinstance(available_models, list) or not all(isinstance(model, str) for model in available_models):
            return

        if not available_models or default_model is None or default_model in available_models:
            return

        raise SuperdeskApiError.badRequestError(
            gettext("'default_model' '{model}' is not one of 'available_models': {models}").format(
                model=default_model, models=", ".join(available_models)
            )
        )
