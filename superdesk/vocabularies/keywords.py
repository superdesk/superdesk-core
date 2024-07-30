from superdesk.core import get_app_config
from superdesk import get_resource_service


def add_missing_keywords(sender, item, **kwargs):
    if get_app_config("KEYWORDS_ADD_MISSING_ON_PUBLISH") and item.get("keywords"):
        get_resource_service("vocabularies").add_missing_keywords(item["keywords"], item.get("language"))
