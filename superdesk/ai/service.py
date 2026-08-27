from typing import Any

from superdesk.core.resources import AsyncResourceService

from .models import AIProvider


class AIProvidersService(AsyncResourceService[AIProvider]):
    async def on_update(self, updates: dict[str, Any], original: AIProvider) -> None:
        if updates.get("api_key") == "":
            # The key is excluded from every response, so a client editing a provider never has it
            # to send back. An empty key therefore means "keep the stored one", the same as leaving
            # the field out of the payload. An explicit ``null`` is the only way to clear it.
            updates.pop("api_key")

        await super().on_update(updates, original)
