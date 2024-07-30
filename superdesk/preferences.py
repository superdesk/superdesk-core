from typing import Literal, Optional, TypedDict
from superdesk.types import User


class NotificationPreferences(TypedDict):
    email: bool
    desktop: bool


def get_user_notification_preferences(user: User, notification: Optional[str] = None) -> NotificationPreferences:
    user_preferences = user.get("user_preferences") or {}

    def is_enabled(preference: Literal["email:notification", "desktop:notification"]) -> bool:
        return bool(user_preferences.get(preference, {}).get("enabled", False))

    email_enabled = is_enabled("email:notification")
    desktop_enabled = is_enabled("desktop:notification")

    if notification is None:
        return NotificationPreferences(
            email=email_enabled,
            desktop=desktop_enabled,
        )

    notification_preferences = user_preferences.get("notifications", {}).get(notification, {})

    return NotificationPreferences(
        email=email_enabled and notification_preferences.get("email") is not False,
        desktop=desktop_enabled and notification_preferences.get("desktop") is not False,
    )
