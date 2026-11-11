"""Rig safety and real child-process checks; no client or power requests."""

import json
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid

import bench


@unittest.skipUnless(os.name == "nt", "Windows-only bench")
class BenchTests(unittest.TestCase):
    def setUp(self):
        self.root = bench.root_for("test-" + uuid.uuid4().hex[:12])
        bench.reset(self.root)

    def tearDown(self):
        # Remove only the exact files this test created, never recurse.
        for path in self.root.iterdir():
            path.unlink()
        self.root.rmdir()

    def healthy(self):
        bench.inject(self.root)
        bench.act(self.root)
        return bench.observe(self.root)

    def test_real_child_roundtrip_and_reset_repeat(self):
        result = self.healthy()
        self.assertTrue(result["ok"])
        self.assertFalse(result["watcher_verified"])
        self.assertFalse(result["battery_verified"])
        old = result["run_id"]
        bench.reset(self.root)
        bench.reset(self.root)
        self.assertNotEqual(bench.read(self.root, "run.json")["run_id"], old)
        self.assertFalse((self.root / "result.json").exists())

    def test_phase_order_is_enforced(self):
        with self.assertRaises(RuntimeError):
            bench.act(self.root)
        with self.assertRaises(RuntimeError):
            bench.observe(self.root)
        bench.inject(self.root)
        with self.assertRaises(RuntimeError):
            bench.inject(self.root)

    def test_missing_result_fails(self):
        self.healthy()
        (self.root / "result.json").unlink()
        with self.assertRaises(FileNotFoundError):
            bench.observe(self.root)

    def test_stale_result_fails(self):
        self.healthy()
        value = bench.read(self.root, "result.json")
        bench.write(self.root, "result.json", {**value, "run_id": uuid.uuid4().hex})
        with self.assertRaises(RuntimeError):
            bench.observe(self.root)

    def test_false_result_fails(self):
        self.healthy()
        value = bench.read(self.root, "result.json")
        bench.write(self.root, "result.json", {**value, "ok": False})
        with self.assertRaises(RuntimeError):
            bench.observe(self.root)

    def test_wrong_schema_fails(self):
        self.healthy()
        value = bench.read(self.root, "result.json")
        bench.write(self.root, "result.json", {**value, "schema": 99})
        with self.assertRaises(RuntimeError):
            bench.observe(self.root)

    def test_claiming_battery_success_fails(self):
        self.healthy()
        value = bench.read(self.root, "result.json")
        bench.write(self.root, "result.json", {**value, "battery_verified": True})
        with self.assertRaises(RuntimeError):
            bench.observe(self.root)

    def test_owner_mismatch_fails(self):
        self.healthy()
        value = bench.read(self.root, "result.json")
        bench.write(self.root, "result.json", {**value, "pid": value["pid"] + 1})
        with self.assertRaises(RuntimeError):
            bench.observe(self.root)

    def test_malformed_result_fails(self):
        self.healthy()
        (self.root / "result.json").write_bytes(b"{bad json")
        with self.assertRaises(json.JSONDecodeError):
            bench.observe(self.root)

    def test_unknown_file_prevents_reset(self):
        other = self.root / "not-owned.txt"
        other.write_bytes(b"preserve me")
        with self.assertRaises(RuntimeError):
            bench.reset(self.root)
        self.assertEqual(other.read_bytes(), b"preserve me")

    def test_bad_marker_prevents_reset(self):
        (self.root / bench.MARKER).write_text("{}", encoding="utf-8")
        before = (self.root / "run.json").read_bytes()
        with self.assertRaises(RuntimeError):
            bench.reset(self.root)
        self.assertEqual((self.root / "run.json").read_bytes(), before)

    def test_outside_namespace_is_refused(self):
        with self.assertRaises(ValueError):
            bench.root_for("../../other")
        with self.assertRaises(ValueError):
            bench.root_for("C:/Users")
        with self.assertRaises((RuntimeError, ValueError)):
            bench.reset(self.root.parent / "not-allowed")

    def test_hardlinks_are_refused_without_touching_target(self):
        target = self.root / "baseline.json"
        target.write_bytes(b"preserve me")
        link = self.root / "stdout.log"
        os.link(target, link)
        with self.assertRaises(RuntimeError):
            bench.reset(self.root)
        self.assertEqual(target.read_bytes(), b"preserve me")

    def test_reset_stops_only_owned_child(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            with bench.process_handle(proc.pid) as handle:
                created = bench.birth(handle)
            state = bench.read(self.root, "run.json")
            bench.write(self.root, "process.json", {"schema": 1, "pid": proc.pid,
                        "birth": created, "run_id": state["run_id"],
                        "specimen": "bench-self-smoke"})
            bench.reset(self.root)
            self.assertIsNotNone(proc.poll())
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)

    def test_mismatched_birth_does_not_kill_live_process(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            with bench.process_handle(proc.pid) as handle:
                created = bench.birth(handle)
            state = bench.read(self.root, "run.json")
            bench.write(self.root, "process.json", {"schema": 1, "pid": proc.pid,
                        "birth": created + 1, "run_id": state["run_id"],
                        "specimen": "bench-self-smoke"})
            bench.reset(self.root)
            self.assertIsNone(proc.poll())
        finally:
            proc.kill()
            proc.wait(timeout=5)

    def test_cli_observe_returns_nonzero_on_broken_probe(self):
        self.healthy()
        (self.root / "result.json").unlink()
        result = subprocess.run([sys.executable, str(Path(bench.__file__).resolve()),
                                 "observe", "--sandbox", self.root.name],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
