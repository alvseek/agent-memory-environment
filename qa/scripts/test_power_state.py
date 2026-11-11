"""Unit checks for request counts and failure cleanup; Windows API is doubled."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/windows"))
from joro_watcher.power import DISPLAY_REQUIRED, EXECUTION_REQUIRED, SYSTEM_REQUIRED, PowerRequest


class FakeAPI:
    def __init__(self, fail_set=None, fail_clear=None, fail_close=False):
        self.calls = []
        self.fail_set, self.fail_clear, self.fail_close = fail_set, fail_clear, fail_close

    def create(self, context):
        self.calls.append(("create",))
        return 42

    def set(self, handle, kind):
        self.calls.append(("set", kind))
        if kind == self.fail_set:
            raise OSError("set failed")

    def clear(self, handle, kind):
        self.calls.append(("clear", kind))
        if kind == self.fail_clear:
            raise OSError("clear failed")

    def close(self, handle):
        self.calls.append(("close",))
        if self.fail_close:
            raise OSError("close failed")


class PowerStateTests(unittest.TestCase):
    def test_counts_are_idempotent_and_released_before_close(self):
        api = FakeAPI()
        with PowerRequest("test", api=api) as request:
            request.acquire()
            request.acquire()
        self.assertEqual(api.calls, [("create",), ("set", SYSTEM_REQUIRED),
                         ("set", EXECUTION_REQUIRED), ("clear", EXECUTION_REQUIRED),
                         ("clear", SYSTEM_REQUIRED), ("close",)])
        request.close()
        self.assertEqual(api.calls.count(("close",)), 1)

    def test_partial_acquisition_cleans_only_successful_requests(self):
        api = FakeAPI(fail_set=EXECUTION_REQUIRED)
        with self.assertRaisesRegex(OSError, "set failed"):
            with PowerRequest("test", api=api) as request:
                request.acquire()
        self.assertIn(("clear", SYSTEM_REQUIRED), api.calls)
        self.assertNotIn(("clear", EXECUTION_REQUIRED), api.calls)
        self.assertEqual(api.calls[-1], ("close",))

    def test_clear_failure_does_not_skip_other_counts_or_close(self):
        api = FakeAPI(fail_clear=EXECUTION_REQUIRED)
        request = PowerRequest("test", api=api)
        request.acquire()
        with self.assertRaises(ExceptionGroup):
            request.close()
        self.assertIn(("clear", SYSTEM_REQUIRED), api.calls)
        self.assertEqual(api.calls[-1], ("close",))
        self.assertIsNone(request.handle)

    def test_close_failure_is_reported_and_retryable(self):
        api = FakeAPI(fail_close=True)
        request = PowerRequest("test", api=api)
        request.acquire()
        with self.assertRaises(ExceptionGroup):
            request.close()
        self.assertEqual(request.handle, 42)
        api.fail_close = False
        request.close()
        self.assertIsNone(request.handle)

    def test_interrupt_and_cleanup_failure_are_both_preserved(self):
        api = FakeAPI(fail_clear=EXECUTION_REQUIRED)
        request = PowerRequest("test", api=api)
        with self.assertRaises(BaseExceptionGroup) as caught:
            with request:
                request.acquire()
                raise KeyboardInterrupt()
        self.assertIsInstance(caught.exception.exceptions[0], KeyboardInterrupt)
        self.assertEqual(api.calls[-1], ("close",))

    def test_display_request_is_explicit(self):
        api = FakeAPI()
        with PowerRequest("test", api=api) as request:
            request.acquire()
            self.assertNotIn(("set", DISPLAY_REQUIRED), api.calls)
            request.acquire(display=True)
            request.acquire(display=True)
        self.assertEqual(api.calls.count(("set", DISPLAY_REQUIRED)), 1)
        self.assertEqual(api.calls.count(("clear", DISPLAY_REQUIRED)), 1)

    def test_closed_request_and_invalid_reason_are_refused(self):
        api = FakeAPI()
        request = PowerRequest("test", api=api)
        request.close()
        with self.assertRaises(RuntimeError):
            request.acquire()
        for reason in ("", "bad\0reason"):
            with self.assertRaises(ValueError):
                PowerRequest(reason, api=api)


if __name__ == "__main__":
    unittest.main()
