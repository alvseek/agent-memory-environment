"""Run one isolated OpenCode agent/tool probe; summarize, never ingest its raw stream."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import bench


def run():
    executable = shutil.which("opencode.exe") or shutil.which("opencode")
    if not executable:
        raise RuntimeError("OpenCode executable not found")
    tag = uuid.uuid4().hex[:12]
    root = bench.base_directory() / bench.PROJECT / ("opencode-lifecycle-" + tag)
    plugin_dir = root / ".opencode/plugins/joro-lifecycle-probe"
    plugin_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__).with_name("opencode_lifecycle_plugin.js"), plugin_dir / "index.js")
    (root / "opencode.json").write_bytes(json.dumps({"plugins": [], "instructions": [],
        "agents": {"joro-lifecycle-probe": {"mode": "primary", "system": "Controlled lifecycle QA only."}}}).encode())
    events = root / "events.jsonl"
    env = os.environ.copy()
    env["JORO_QA_EVENT_FILE"] = str(events)
    command = [executable, "run", "--standalone", "--format", "json", "--agent",
               "joro-lifecycle-probe", "--title", "Joro QA " + tag,
               "Call joro_probe once and then reply PROBE_DONE."]
    # Raw verbose output goes to files outside Git, never a tool result.
    with (root / "client-stream.jsonl").open("wb") as out, (root / "client-stderr.log").open("wb") as err:
        proc = subprocess.Popen(command, cwd=root, env=env, stdout=out, stderr=err,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            exit_code = proc.wait(timeout=90)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            exit_code = -1
    recorded = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()] if events.exists() else []
    kinds = [e["event"] for e in recorded]
    valid = exit_code == 0 and kinds.count("controlled_tool_started") == 1 and kinds.count("controlled_tool_finished") == 1 and "context_dispatch" in kinds and "session_wait_returned" in kinds
    report = {"exit_code": exit_code, "probe_passed": valid, "events": recorded,
              "global_configuration_changed": False, "watcher_verified": False,
              "scope": "private-OpenCode-server-one-tool-turn-no-approval-wait-assertion",
              "test_session_cleanup": "not-yet-verified"}
    (root / "report.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({"report": str(root / "report.json"), "probe_passed": valid,
                      "exit_code": exit_code, "events": kinds,
                      "stream_bytes": (root / "client-stream.jsonl").stat().st_size,
                      "stderr_bytes": (root / "client-stderr.log").stat().st_size}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(run())
