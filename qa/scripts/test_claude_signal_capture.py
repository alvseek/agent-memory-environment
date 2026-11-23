"""Focused privacy/isolation checks; never starts Claude or modifies live Joro."""

import concurrent.futures
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

import claude_signal_capture as probe


class SignalCaptureTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="joro-signals-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def record(self, **fields):
        value = {"hook_event_name": "Stop", "session_id": "session-1", **fields}
        path = probe.capture(io.BytesIO(json.dumps(value).encode()), self.root)
        return json.loads(path.read_bytes())

    def test_only_allowlisted_metadata_survives(self):
        entry = self.record(
            prompt="PRIVATE", last_assistant_message="PRIVATE", message="PRIVATE",
            transcript_path="PRIVATE", tool_input={"command": "PRIVATE"},
            tool_response={"stdout": "PRIVATE"}, error_details="PRIVATE",
            prompt_id="prompt-1", stop_hook_active=False,
            background_tasks=[{"id": "job-1", "type": "shell", "status": "running",
                               "description": "PRIVATE", "command": "PRIVATE"}],
            session_crons=[{"id": "cron-1", "prompt": "PRIVATE", "schedule": "PRIVATE"}],
        )
        self.assertNotIn("PRIVATE", json.dumps(entry))
        self.assertEqual(entry["background_tasks"], [{"id": "job-1", "type": "shell", "status": "running"}])
        self.assertEqual(entry["session_crons"], [{"id": "cron-1"}])
        self.assertFalse(entry["stop_hook_active"])

    def test_absent_null_empty_and_invalid_are_distinct(self):
        absent = self.record()
        null = self.record(prompt_id=None, background_tasks=None)
        empty = self.record(background_tasks=[])
        invalid = self.record(prompt_id={"secret": "PRIVATE"}, stop_hook_active="PRIVATE")
        self.assertNotIn("prompt_id", absent["present_fields"])
        self.assertIn("prompt_id", null["present_fields"])
        self.assertIsNone(null["prompt_id"])
        self.assertIn("background_tasks", null["invalid_fields"])
        self.assertEqual(empty["background_tasks"], [])
        self.assertEqual(empty["background_tasks_total"], 0)
        self.assertEqual(invalid["invalid_fields"], ["prompt_id", "stop_hook_active"])
        self.assertNotIn("PRIVATE", json.dumps(invalid))

    def test_notification_type_and_task_ids_are_retained(self):
        entry = self.record(hook_event_name="Notification", notification_type="idle_prompt",
                            prompt_id="new", task_id="task-1", tool_use_id="toolu_1")
        self.assertEqual(entry["notification_type"], "idle_prompt")
        self.assertEqual(entry["task_id"], "task-1")
        self.assertEqual(entry["prompt_id"], "new")

    def test_record_bounds_are_explicit_not_silent(self):
        entry = self.record(background_tasks=[{"id": str(i)} for i in range(probe.MAX_ITEMS + 1)])
        self.assertTrue(entry["background_tasks_clipped"])
        self.assertEqual(entry["background_tasks_total"], probe.MAX_ITEMS + 1)
        self.assertEqual(len(entry["background_tasks"]), probe.MAX_ITEMS)
        self.assertLess(len(json.dumps(entry).encode()), probe.MAX_OUTPUT)
        with self.assertRaises(ValueError):
            probe.capture(io.BytesIO(b" " * (probe.MAX_INPUT + 1)), self.root)

    def test_invalid_payloads_and_unknown_events_write_nothing(self):
        for raw in (b'{"prompt":"PRIVATE",', b"[]",
                    b'{"hook_event_name":"NotAnEvent","prompt":"PRIVATE"}'):
            with self.assertRaises((ValueError, TypeError)):
                probe.capture(io.BytesIO(raw), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_concurrent_processes_publish_complete_unique_files(self):
        def invoke(number):
            return subprocess.run(
                [sys.executable, str(Path(probe.__file__)), "capture", str(self.root)],
                input=json.dumps({"hook_event_name": "PreToolUse", "session_id": f"test-{number}"}),
                capture_output=True, text=True, timeout=20,
            )
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(invoke, range(12)))
        self.assertTrue(all(p.returncode == 0 and not p.stdout and not p.stderr for p in results))
        files = list(self.root.glob("*.json"))
        self.assertEqual(len(files), 12)
        records = [json.loads(path.read_bytes()) for path in files]
        self.assertEqual({r["session_id"] for r in records}, {f"test-{i}" for i in range(12)})
        self.assertEqual(len({r["capture_id"] for r in records}), 12)
        self.assertFalse(list(self.root.glob("*.pending")))

    def test_io_failure_is_visible_and_does_not_leave_partial_record(self):
        with patch.object(Path, "replace", side_effect=PermissionError("PRIVATE")):
            with self.assertRaises(PermissionError):
                self.record()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_failure_exit_never_echoes_payload(self):
        result = subprocess.run(
            [sys.executable, str(Path(probe.__file__)), "capture", str(self.root)],
            input='{"prompt":"PRIVATE",', capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("PRIVATE", result.stderr)
        self.assertIn("JSONDecodeError", result.stderr)

    def test_draft_is_inert_and_refuses_overwrite(self):
        directory = self.root / "new-draft"
        report = probe.draft(directory)
        self.assertFalse(report["activated"])
        self.assertFalse((directory / ".claude").exists())
        self.assertFalse((directory / "settings.json").exists())
        settings = json.loads(Path(report["draft"]).read_bytes())
        self.assertEqual(set(settings["hooks"]), set(probe.EVENTS))
        self.assertIn("Notification", settings["hooks"])
        self.assertNotIn("permissions", settings)
        self.assertFalse(list((directory / "events").iterdir()))
        with self.assertRaises(FileExistsError):
            probe.draft(directory)

    def test_scoped_draft_filters_before_publishing(self):
        target = uuid.uuid4()
        proposal = probe.draft(self.root / "draft", target)
        hooks = json.loads(Path(proposal["draft"]).read_bytes())["hooks"]
        self.assertEqual(set(hooks), {"Stop", "Notification"})
        directory = Path(proposal["events"])
        for event in hooks:
            command = hooks[event][0]["hooks"][0]["command"]
            self.assertTrue(command.endswith(f" --session-id {target}"))
            for identity in ({}, {"session_id": None}, {"session_id": str(uuid.uuid4())},
                             {"session_id": str(target)}):
                before = set(directory.iterdir())
                value = {"hook_event_name": event, "message": "PRIVATE", **identity}
                p = subprocess.run(command, shell=True, input=json.dumps(value), text=True,
                                   capture_output=True, timeout=10)
                self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""))
                added = set(directory.iterdir()) - before
                if identity.get("session_id") == str(target):
                    self.assertEqual(len(added), 1)
                    record = added.pop().read_text()
                    self.assertNotIn("PRIVATE", record)
                    self.assertEqual(json.loads(record)["event"], event)
                else:
                    self.assertFalse(added)

    def test_capture_does_not_create_missing_directory(self):
        with self.assertRaises(ValueError):
            probe.capture(io.BytesIO(b"{}"), self.root / "missing")
        self.assertFalse((self.root / "missing").exists())

    def test_invalid_draft_command_creates_nothing(self):
        with self.assertRaises(ValueError):
            probe.draft(self.root / "missing" / "$invalid")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_draft_rejects_linked_ancestor_before_creating_directories(self):
        with patch.object(Path, "is_junction", lambda path: path == self.root):
            with self.assertRaises(ValueError):
                probe.draft(self.root / "nested" / "draft")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_failed_draft_write_rolls_back_without_removing_foreign_file(self):
        destination = self.root / "new-parent" / "draft"
        foreign = destination.parent / "not-owned"

        def fail_after_partial_write(config, stream, **kwargs):
            stream.write("{")
            foreign.write_bytes(b"keep")
            raise OSError("write failed")

        with patch.object(json, "dump", side_effect=fail_after_partial_write):
            with self.assertRaisesRegex(OSError, "write failed"):
                probe.draft(destination)
        self.assertFalse(destination.exists())
        self.assertEqual(foreign.read_bytes(), b"keep")
        self.assertFalse(probe.draft(destination)["activated"])

    def test_linked_directory_is_refused_before_reading_input(self):
        with patch.object(Path, "is_junction", return_value=True):
            with self.assertRaises(ValueError):
                probe.capture(io.BytesIO(b"{}"), self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_output_bound_refuses_instead_of_publishing_partial_metadata(self):
        with patch.object(probe, "MAX_OUTPUT", 1):
            with self.assertRaises(ValueError):
                self.record()
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
