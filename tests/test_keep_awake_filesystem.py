"""One real boundary: filesystem. Process identity is doubled; no desktop UI.

Preconditions are created through the production writer/logger, not saved seeds.
TemporaryDirectory owns teardown. No upstream fixture is needed.
"""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from contextlib import nullcontext

WINDOWS = Path(__file__).resolve().parents[1] / "scripts/windows"
sys.path.insert(0, str(WINDOWS))
from joro_watcher import event_log, tray

spec = importlib.util.spec_from_file_location("filesystem_helper", WINDOWS / "keep_awake.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class FilesystemTests(unittest.TestCase):
    def test_log_rotation_keeps_five_bounded_files(self):
        with tempfile.TemporaryDirectory(prefix="joro-log-") as directory:
            # This test crosses only the filesystem, not native synchronization.
            with patch.object(event_log, "locked", return_value=nullcontext()):
                for index in range(850):
                    event_log.record("test", directory=directory, index=index, detail="x" * 8000)
            files = list(Path(directory).glob("keep-awake.log*"))
            self.assertEqual(len(files), 5)
            self.assertTrue(all(p.stat().st_size <= 1024 * 1024 for p in files))
            newest = (Path(directory) / "keep-awake.log").read_text(encoding="utf-8")
            self.assertIn('"index": 849', newest)
            self.assertNotIn('"index": 0,', newest)

    def test_published_helper_reports_drive_tray_states(self):
        with tempfile.TemporaryDirectory(prefix="joro-report-") as directory:
            root = Path(directory)
            with patch.object(helper, "ROOT", root), patch.object(helper, "birth", return_value=123):
                value = {"pid": 1, "birth": 123, "updated_at": time.time(),
                         "power_requested": False, "clients": []}
                helper.write(root / "helper.json", value)
                self.assertEqual(tray.presentation(tray.observe(helper))[0], "idle")
                helper.write(root / "helper.json", {**value, "power_requested": True, "clients": ["opencode"]})
                self.assertEqual(tray.presentation(tray.observe(helper))[0], "awake")
                helper.write(root / "helper.json", {**value, "uncertain_claims": 1, "power_requested": True})
                self.assertEqual(tray.presentation(tray.observe(helper))[0], "warning")
                helper.write(root / "helper.json", {**value, "updated_at": time.time() - 30})
                self.assertIn("not reporting", tray.presentation(tray.observe(helper))[1])
                (root / "helper.json").write_text("{broken", encoding="utf-8")
                self.assertEqual(tray.presentation(tray.observe(helper))[0], "warning")
                (root / "helper.json").unlink()
                self.assertEqual(tray.presentation(tray.observe(helper))[0], "warning")
                helper.write(root / "helper-error.json", {"error": "synthetic failure"})
                self.assertIn("helper failed", tray.presentation(tray.observe(helper))[1])


if __name__ == "__main__":
    unittest.main()
