"""Integration boundary: PowerRequest -> real Windows power-request handles.

No upstream state fixture is needed: the test creates its own native handle.
Client lifecycle, registry, installer and battery conditions are not exercised.
"""

from pathlib import Path
import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "joro-awake/scripts/windows"))
from joro_watcher.power import EXECUTION_REQUIRED, SYSTEM_REQUIRED, NativePowerAPI, PowerRequest


def exercise_lifecycle(request: PowerRequest, duration: float = 0.0):
    api = request.api
    handle = request.handle
    try:
        if not api.is_valid(handle):
            raise AssertionError("Native handle was not valid after creation")
        request.acquire()
        if request.acquired != [SYSTEM_REQUIRED, EXECUTION_REQUIRED]:
            raise AssertionError("Expected system and execution requests, not a display hold")
        request.acquire()
        if request.acquired != [SYSTEM_REQUIRED, EXECUTION_REQUIRED]:
            raise AssertionError("Repeated acquire added request counts")
        time.sleep(duration)
        request.release()
        if request.acquired:
            raise AssertionError("Acquired request counts were not cleared")
        request.close()
        if api.is_valid(handle):
            raise AssertionError("Native handle remained valid after close")
        request.close()  # Idempotent cleanup must not attempt a second CloseHandle.
    finally:
        # Also handles a deliberate close-omission mutation; never leak native state.
        if api.is_valid(handle):
            try:
                request.release()
            finally:
                api.close(handle)
                request.handle = None
                request.acquired.clear()


@unittest.skipUnless(os.name == "nt", "Real Windows native dependency required")
class NativePowerIntegrationTests(unittest.TestCase):
    def test_acquire_release_and_close_real_handle(self):
        exercise_lifecycle(PowerRequest("Joro QA bounded two-second native probe"), 2.0)

    def test_independent_request_handles(self):
        api = NativePowerAPI()
        first = PowerRequest("Joro QA owner one", api=api)
        second = PowerRequest("Joro QA owner two", api=api)
        saved = [first.handle, second.handle]
        try:
            first.acquire()
            second.acquire()
            first.close()
            self.assertFalse(api.is_valid(saved[0]))
            self.assertTrue(api.is_valid(saved[1]))
            self.assertEqual(second.acquired, [SYSTEM_REQUIRED, EXECUTION_REQUIRED])
        finally:
            first.close()
            second.close()
        self.assertFalse(api.is_valid(saved[1]))

    def test_operation_failure_still_closes_real_handle(self):
        api = NativePowerAPI()
        request = PowerRequest("Joro QA error cleanup", api=api)
        handle = request.handle
        with self.assertRaisesRegex(RuntimeError, "synthetic work failure"):
            with request:
                request.acquire()
                raise RuntimeError("synthetic work failure")
        self.assertFalse(api.is_valid(handle))

    def test_negative_control_detects_close_omission_and_cleans_it(self):
        api = NativePowerAPI()
        request = PowerRequest("Joro QA close-omission negative control", api=api)
        handle = request.handle
        with patch.object(request, "close", return_value=None):
            with self.assertRaisesRegex(AssertionError, "remained valid"):
                exercise_lifecycle(request)
        self.assertFalse(api.is_valid(handle))


if __name__ == "__main__":
    unittest.main()
