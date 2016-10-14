
from raven.contrib.flask import Sentry


class SuperdeskSentry():
    """Sentry proxy that will do nothing in case sentry is not configured."""

    def __init__(self, app):
        if app.config.get('SENTRY_DSN'):
            app.config.setdefault('SENTRY_NAME', app.config.get('SERVER_NAME'))
            self.sentry = Sentry(app, register_signal=False, wrap_wsgi=False)
        else:
            self.sentry = None

    def captureException(self, exc_info=None, **kwargs):
        if self.sentry:
            self.sentry.captureException(exc_info, **kwargs)

    def captureMessage(self, message, **kwargs):
        if self.sentry:
            self.sentry.captureMessage(message, **kwargs)
