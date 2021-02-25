import superdesk
from flask_babel import lazy_gettext


def init_app(app) -> None:
    superdesk.register_default_user_preference(
        "monitoring:view",
        {
            "type": "string",
            "allowed": ["list", "swimlane"],
            "view": "list",
            "default": "list",
        },
        label=lazy_gettext("Monitoring view"),
        category=lazy_gettext("monitoring"),
    )

    superdesk.register_default_session_preference("monitoring:view:session", None)
