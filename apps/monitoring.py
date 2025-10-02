import superdesk
from quart_babel import lazy_gettext


def init_app(app) -> None:
    superdesk.register_default_user_preference(
        "monitoring:view",
        {
            "type": "string",
            "view": "list",
            "default": "list",
        },
        label=lazy_gettext("Monitoring view"),
    )

    superdesk.register_default_session_preference("monitoring:view:session", None)
