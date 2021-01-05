import unittest

from unittest.mock import patch
from superdesk.default_settings import celery_queue


class SettingsTestCase(unittest.TestCase):
    def test_celery_queue(self):
        with patch("superdesk.default_settings.os.environ.get", return_value="") as env:
            self.assertEqual("foo", celery_queue("foo"))
            env.assert_called_with("SUPERDESK_CELERY_PREFIX", "")
        with patch("superdesk.default_settings.os.environ.get", return_value="prefix"):
            self.assertEqual("prefixfoo", celery_queue("foo"))
