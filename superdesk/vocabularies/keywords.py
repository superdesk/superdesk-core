from superdesk.core import get_app_config
from superdesk import get_resource_service


async def add_missing_keywords(item: dict, after_scheduled: bool) -> None:
    if get_app_config("KEYWORDS_ADD_MISSING_ON_PUBLISH") and item.get("keywords"):
        await get_resource_service("vocabularies").add_missing_keywords_async(item["keywords"], item.get("language"))
