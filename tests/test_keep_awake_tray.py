"""Tray decisions without launching a desktop UI or touching installed state."""

from contextlib import nullcontext
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import threading

WINDOWS = Path(__file__).resolve().parents[1] / "scripts/windows"
sys.path.insert(0, str(WINDOWS))
from joro_watcher import event_log, tray
import keep_awake as helper


class TrayTests(unittest.TestCase):
    def test_idle_is_not_an_open_client_process(self):
        self.assertEqual(tray.presentation({"running": True, "power_requested": False,
                                           "clients": ["opencode"]})[0], "idle")

    def test_awake_names_the_reporting_clients(self):
        state, title = tray.presentation({"running": True, "power_requested": True,
                                          "clients": ["claude", "opencode"]})
        self.assertEqual(state, "awake")
        self.assertIn("Claude Code, OpenCode", title)

    def test_missing_helper_is_not_idle(self):
        self.assertEqual(tray.presentation({"running": False})[0], "warning")

    def test_uncertainty_takes_precedence_over_power_request(self):
        self.assertEqual(tray.presentation({"running": True, "power_requested": True,
                                           "uncertain_claims": 1})[0], "warning")

    def test_error_takes_precedence_over_everything(self):
        self.assertEqual(tray.presentation({"running": True, "power_requested": True,
                                           "error": "unreadable"})[0], "warning")

    def test_log_rotation_is_five_files_total_and_closes_each_writer(self):
        with patch.object(event_log, "locked", return_value=nullcontext()), \
             patch.object(Path, "mkdir"), patch.object(event_log, "StrictRotatingHandler") as handler:
            event_log.record("start", directory=WINDOWS, source="test")
        self.assertEqual(handler.call_args.kwargs["maxBytes"], 1024 * 1024)
        self.assertEqual(handler.call_args.kwargs["backupCount"], 4)
        handler.return_value.emit.assert_called_once()
        handler.return_value.close.assert_called_once()

    def test_log_message_is_bounded(self):
        with patch.object(event_log, "locked", return_value=nullcontext()), \
             patch.object(Path, "mkdir"), patch.object(event_log, "StrictRotatingHandler") as handler:
            event_log.record("error", directory=WINDOWS, error="x" * 20000)
        self.assertLessEqual(len(handler.return_value.emit.call_args.args[0].msg), 8192)

    def test_log_failure_is_reported_without_raising(self):
        with patch.object(event_log, "_record", side_effect=OSError("disk")), patch.object(event_log.sys, "stderr"):
            self.assertIn("OSError", event_log.record("test"))
        with patch.object(event_log, "_record"):
            self.assertIsNone(event_log.record("recovered"))
            self.assertIsNone(event_log.LAST_ERROR)

    def test_exit_failure_keeps_warning_icon_and_process_alive(self):
        icon, stopped, failure = MagicMock(), threading.Event(), {}
        with patch.object(tray, "stop_helper", side_effect=RuntimeError("failed")), patch.object(tray, "record"):
            self.assertFalse(tray.exit_monitoring(None, icon, {"warning": "warning"}, stopped, failure))
        self.assertEqual(icon.icon, "warning")
        self.assertFalse(stopped.is_set())
        icon.stop.assert_not_called()

    def test_exit_success_removes_icon_after_confirmed_shutdown(self):
        icon, stopped = MagicMock(), threading.Event()
        with patch.object(tray, "stop_helper") as stop, patch.object(tray, "record"):
            self.assertTrue(tray.exit_monitoring(None, icon, {}, stopped, {}))
        stop.assert_called_once()
        self.assertTrue(stopped.is_set())
        icon.stop.assert_called_once()

    def test_observer_failure_warns_then_recovers_on_next_tick(self):
        icon, icons = MagicMock(), {"warning": "warning", "idle": "idle"}
        with patch.object(tray, "observe", side_effect=RuntimeError("unexpected")), patch.object(tray, "record"):
            self.assertIsNone(tray.observe_once(None, icon, icons, {}, None))
        self.assertEqual(icon.icon, "warning")
        with patch.object(tray, "observe", return_value={"running": True}), \
             patch.object(tray, "record", return_value=None):
            self.assertEqual(tray.observe_once(None, icon, icons, {}, None)[0], "idle")

    def test_logging_failure_changes_healthy_icon_to_warning(self):
        icon = MagicMock()
        with patch.object(tray, "observe", return_value={"running": True}), \
             patch.object(tray, "record", return_value="Log unavailable"):
            self.assertIsNone(tray.observe_once(None, icon, {"idle": "idle", "warning": "warning"}, {}, None))
        self.assertEqual(icon.icon, "warning")

    def test_live_tray_is_not_spawned_twice(self):
        root = MagicMock()
        (root / "tray.json").read_text.return_value = '{"pid": 42, "birth": 123}'
        with patch.object(helper, "ROOT", root), patch.object(helper, "birth", return_value=123), \
             patch.object(helper.subprocess, "Popen") as spawn:
            helper.start_tray()
        spawn.assert_not_called()

    def test_tray_startup_failure_does_not_prevent_power_request(self):
        kernel, root, request = MagicMock(), MagicMock(), MagicMock()
        kernel.WaitForSingleObject.return_value = 0
        with patch.object(helper, "K", kernel), patch.object(helper, "ROOT", root), \
             patch.object(helper, "birth", return_value=123), patch.object(helper, "write") as write, \
             patch.object(helper, "record", return_value=None), \
             patch.object(helper, "start_tray", side_effect=RuntimeError("tray unavailable")), \
             patch.object(helper, "state", return_value={"active_count": 1, "clients": ["opencode"],
                                                        "uncertain_claims": 0}), \
             patch.object(helper, "PowerRequest", return_value=request):
            helper.run()
        request.acquire.assert_called_once()
        request.close.assert_called_once()
        self.assertTrue(write.call_args.args[1]["power_requested"])

    def test_stop_helper_requires_explicit_exit_confirmation(self):
        value = MagicMock(__file__="helper.py")
        result = MagicMock(returncode=0, stdout='{"running": true}')
        with patch.object(tray.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "not confirmed"):
                tray.stop_helper(value)


if __name__ == "__main__":
    unittest.main()
