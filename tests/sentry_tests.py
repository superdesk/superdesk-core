import flask
import unittest
from superdesk.factory.sentry import SuperdeskSentry


class SentryTestCase(unittest.TestCase):
    def test_sentry_not_configured(self):
        app = flask.Flask(__name__)
        sentry = SuperdeskSentry(app)
        self.assertIsNone(sentry.captureMessage("test"))
        self.assertIsNone(sentry.captureException())
