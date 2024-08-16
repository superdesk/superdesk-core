from typing import Optional, TypedDict
from superdesk.types import User


class NotificationPreferences(TypedDict):
    email: bool
    desktop: bool


def get_user_notification_preferences(user: User, notification: Optional[str] = None) -> NotificationPreferences:
    user_preferences = user.get("user_preferences") or {}

    def is_enabled(preference: str) -> bool:
        return bool(user_preferences.get(preference, {}).get("enabled", False))

    email_enabled = is_enabled("email:notification")
    desktop_enabled = is_enabled("desktop:notification")

    if notification is None:
        return NotificationPreferences(
            email=email_enabled,
            desktop=desktop_enabled,
        )

    notification_preferences = user_preferences.get("notifications", {}).get(notification)
    if notification_preferences is None:
        # BC: Check for the old email:notification:<notification> preference
        email_notification_name = f"email:notification:{notification}"
        user_email_preferences = user_preferences.get("notifications", {}).get(email_notification_name)
        if user_email_preferences:
            return NotificationPreferences(
                email=email_enabled and user_email_preferences.get("email"),
                desktop=desktop_enabled,
            )
        else:
            return NotificationPreferences(
                email=email_enabled,
                desktop=desktop_enabled,
            )

    return NotificationPreferences(
        email=email_enabled and notification_preferences.get("email") is not False,
        desktop=desktop_enabled and notification_preferences.get("desktop") is not False,
    )
