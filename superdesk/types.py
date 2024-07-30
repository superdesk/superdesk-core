from typing import TypedDict, Dict, Any, List


class WebsocketMessageFilterConditions(TypedDict, total=False):
    include: Dict[str, List[str]]
    exclude: Dict[str, List[str]]


class WebsocketMessageData(TypedDict, total=False):
    event: str
    filters: WebsocketMessageFilterConditions
    extra: Dict[str, Any]
    _created: str  # isoformat
    _process: int


class ItemAuthor(TypedDict):
    uri: str
    parent: str
    name: str
    role: str
    jobtitle: str
    sub_label: str


class Item(TypedDict, total=False):
    headline: str
    slugline: str
    authors: List[ItemAuthor]
    extra: Dict[str, Any]


class UserMandatory(TypedDict):
    email: str
    username: str


class DefaultNotificationPreference(TypedDict, total=False):
    enabled: bool


class NotificationPreference(TypedDict, total=False):
    email: bool
    desktop: bool


UserPreferences = TypedDict(
    "UserPreferences",
    {
        "notifications": Dict[str, NotificationPreference],
        "email:notification": DefaultNotificationPreference,
        "desktop:notification": DefaultNotificationPreference,
    },
    total=False,
)


class User(UserMandatory, total=False):
    user_preferences: UserPreferences
    needs_activation: bool
    is_enabled: bool
    is_active: bool
