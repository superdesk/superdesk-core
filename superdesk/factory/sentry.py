from quart import Quart
import sentry_sdk

from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration


SENTRY_DSN = "SENTRY_DSN"


class SuperdeskSentry:
    """Sentry proxy that will do nothing in case sentry is not configured."""

    def __init__(self, app: Quart) -> None:
        self.enabled = False
        if app.config.get(SENTRY_DSN):
            self.enabled = True
            dsn = app.config[SENTRY_DSN]
            if "verify_ssl" not in dsn:
                dsn += "?verify_ssl=0"
            sentry_sdk.init(
                dsn=dsn,
                send_default_pii=True,
                server_name=app.config.get("SERVER_DOMAIN"),
                debug=app.debug,
                traces_sample_rate=app.config.get("SENTRY_TRACES_SAMPLE_RATE"),
                profiles_sample_rate=app.config.get("SENTRY_PROFILES_SAMPLE_RATE"),
                integrations=[
                    CeleryIntegration(
                        monitor_beat_tasks=True,
                    ),
                ],
                disabled_integrations=[FlaskIntegration()],
            )

    def captureException(self, exc_info=None, **kwargs) -> None:
        if self.enabled:
            sentry_sdk.capture_exception(exc_info)

    def captureMessage(self, message, **kwargs) -> None:
        if self.enabled:
            sentry_sdk.capture_message(message)
