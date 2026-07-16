from unittest import TestCase

from superdesk.publish_async.utils import compute_retry_timeout_minutes


class RetryTimeoutUtilsTestCase(TestCase):
    def test_returns_initial_delay_for_first_retry(self):
        timeout = compute_retry_timeout_minutes(
            retry_attempt=0,
            initial_retry_delay_minutes=1,
            max_retry_delay_minutes=120,
        )

        self.assertEqual(timeout, 1)

    def test_doubles_timeout_per_retry_attempt(self):
        timeout = compute_retry_timeout_minutes(
            retry_attempt=3,
            initial_retry_delay_minutes=1,
            max_retry_delay_minutes=120,
        )

        self.assertEqual(timeout, 8)

    def test_caps_timeout_to_max_delay(self):
        timeout = compute_retry_timeout_minutes(
            retry_attempt=10,
            initial_retry_delay_minutes=1,
            max_retry_delay_minutes=120,
        )

        self.assertEqual(timeout, 120)

    def test_clamps_invalid_delays_to_minimum_one_minute(self):
        timeout = compute_retry_timeout_minutes(
            retry_attempt=0,
            initial_retry_delay_minutes=0,
            max_retry_delay_minutes=0,
        )

        self.assertEqual(timeout, 1)

    def test_negative_retry_attempt_is_treated_as_zero(self):
        timeout = compute_retry_timeout_minutes(
            retry_attempt=-2,
            initial_retry_delay_minutes=2,
            max_retry_delay_minutes=120,
        )

        self.assertEqual(timeout, 2)
