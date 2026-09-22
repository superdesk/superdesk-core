import json
import logging
import zlib

from unittest import TestCase, mock

from celery.signals import after_setup_logger

import superdesk.logging as sd_logging


class GraylogTestCase(TestCase):
    def setUp(self):
        self.root = logging.getLogger()
        self.root_handlers = list(self.root.handlers)
        sd_logging._graylog_handler = None

    def tearDown(self):
        self.root.handlers = self.root_handlers
        sd_logging._graylog_handler = None

    def test_disabled_without_host(self):
        sd_logging.configure_graylog({"GRAYLOG_HOST": None})
        self.assertIsNone(sd_logging._graylog_handler)
        self.assertEqual(self.root_handlers, self.root.handlers)

    def test_handler_added_to_root(self):
        config = {
            "GRAYLOG_HOST": "graylog",
            "GRAYLOG_PORT": 12345,
            "GRAYLOG_FACILITY": "sd",
            "GRAYLOG_LEVEL": "WARNING",
        }
        sd_logging.configure_graylog(config)
        sd_logging.configure_graylog(config)

        handler = sd_logging._graylog_handler
        self.assertIsNotNone(handler)
        self.assertEqual(1, self.root.handlers.count(handler))
        self.assertEqual(("graylog", 12345), (handler.host, handler.port))
        self.assertEqual("sd", handler.facility)
        self.assertEqual(logging.WARNING, handler.level)

    def test_handler_readded_after_celery_logging_setup(self):
        sd_logging.configure_graylog({"GRAYLOG_HOST": "graylog"})
        self.root.handlers = []  # celery worker hijacking root logger
        after_setup_logger.send(
            sender=None, logger=self.root, loglevel=logging.INFO, logfile=None, format="", colorize=False
        )
        self.assertIn(sd_logging._graylog_handler, self.root.handlers)

    def test_message_sent(self):
        sd_logging.configure_graylog({"GRAYLOG_HOST": "graylog", "GRAYLOG_FACILITY": "sd"})
        with mock.patch.object(sd_logging._graylog_handler, "send") as send:
            try:
                raise ValueError("boom")
            except ValueError:
                logging.getLogger("superdesk.test").exception("failed")

        send.assert_called_once()
        gelf = json.loads(zlib.decompress(send.call_args[0][0]))
        self.assertEqual("sd", gelf["facility"])
        self.assertEqual("superdesk.test", gelf["_logger"])
        self.assertTrue(gelf["short_message"].startswith("failed\nTraceback"))
        self.assertIn("ValueError: boom", gelf["short_message"])
