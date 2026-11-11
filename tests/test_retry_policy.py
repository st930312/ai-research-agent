"""Transient source retry and exponential backoff regression tests."""
import unittest
import urllib.error
from unittest.mock import patch
from src.retry_policy import with_backoff, transient_error, backoff_delay


class RetryPolicyTests(unittest.TestCase):
    @patch("src.retry_policy.time.sleep")
    @patch("src.retry_policy.random.uniform", side_effect=lambda lo, hi: lo)
    def test_transient_429_retries_twice_with_exponential_backoff(self, _rng, sleep):
        calls = []
        def failing():
            calls.append(True)
            if len(calls) < 3:
                raise urllib.error.HTTPError("https://example.org", 429, "Rate limit",
                                             {"Retry-After": "0"}, None)
            return "ok"
        self.assertEqual(with_backoff(failing, label="rss"), "ok")
        self.assertEqual(len(calls), 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [3.0, 6.0])

    @patch("src.retry_policy.time.sleep")
    def test_nontransient_404_does_not_retry(self, sleep):
        calls = []
        def missing():
            calls.append(1)
            raise urllib.error.HTTPError("https://example.org", 404, "Missing", {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            with_backoff(missing, label="rss")
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    @patch("src.retry_policy.time.sleep")
    def test_parser_failure_does_not_retry(self, sleep):
        with self.assertRaises(ValueError):
            with_backoff(lambda: (_ for _ in ()).throw(ValueError("Invalid XML")))
        sleep.assert_not_called()

    @patch("src.retry_policy.random.uniform", side_effect=lambda lo, hi: lo)
    def test_retry_after_is_respected(self, _rng):
        err = urllib.error.HTTPError("https://example.org", 429, "Rate limit",
                                     {"Retry-After": "18"}, None)
        self.assertEqual(backoff_delay(1, err), 18.0)

    def test_transient_error_classification(self):
        self.assertTrue(transient_error(urllib.error.URLError("timeout")))
        self.assertFalse(transient_error(ValueError("parsing")))


if __name__ == "__main__":
    unittest.main()
