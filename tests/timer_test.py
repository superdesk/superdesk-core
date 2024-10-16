import time
import unittest

from unittest.mock import patch, ANY
from superdesk.timer import timer


class TimerTestCase(unittest.TestCase):
    @patch("superdesk.timer.logger")
    def test_timer(self, logger):
        with timer("foo"):
            time.sleep(0.1)
        logger.info.assert_called_once_with("%s: %.3fms", "foo", ANY)
        self.assertAlmostEqual(100, int(logger.info.call_args[0][2]), delta=50)  # 50ms tolerance
