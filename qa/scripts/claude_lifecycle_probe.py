"""Measure Claude Code hook timing; allow one fixed harmless sandbox command only."""

from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

import bench


def capture_hook(event_file: Path, *, continue_stop_once: bool = False) -> int:
    value = json.load(sys.stdin)
    # Deliberately do not retain prompt/tool inputs or assistant text.
    event = {"time_ns": time.time_ns(), "event": value.get("hook_event_name"),
             "session": value.get("session_id"), "tool": value.get("tool_name"),
             "tool_use_id": value.get("tool_use_id"),
             "stop_hook_active": value.get("stop_hook_active"),
             "prompt_id": value.get("prompt_id")}
    with event_file.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event) + "\n")
    if continue_stop_once and value.get("hook_event_name") == "Stop" and not value.get("stop_hook_active"):
        print(json.dumps({"decision": "block", "reason":
                         "Controlled QA: continue once, use no tools, and respond PROBE_CONTINUED."}))
    return 0


def controlled_work(event_file: Path) -> int:
    for event in ("controlled_tool_started", "controlled_tool_finished"):
        with event_file.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"event": event, "time_ns": time.time_ns()}) + "\n")
        if event == "controlled_tool_started":
            installed = os.environ.get("JORO_QA_INSTALLED_HELPER")
            if installed:
                target = Path(installed)
                sys.path.insert(0, str(target.parent))
                spec = importlib.util.spec_from_file_location("joro_installed_probe", target)
                helper = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(helper)
                owner = helper.claude_owner()
                claims = [json.loads(p.read_text(encoding="utf-8")) for p in helper.CLAIMS.glob("*.json")]
                present = any(c["client"] == "claude" and c["pid"] == owner for c in claims)
                with event_file.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps({"event": "installed_claude_claim", "time_ns": time.time_ns(),
                                             "present": present, "owner_pid": owner}) + "\n")
                if not present:
                    raise RuntimeError("Installed Claude hook did not publish its real owner's claim")
            time.sleep(2)
    print("JORO_CONTROLLED_PROBE")
    return 0


def run(*, deny: bool = False, stop_once: bool = False, with_joro: bool = False) -> int:
    executable = shutil.which("claude.exe") or shutil.which("claude")
    if not executable:
        raise RuntimeError("Claude Code executable not available")
    root = bench.base_directory() / bench.PROJECT / ("lifecycle-" + uuid.uuid4().hex[:12])
    # This is a retained experiment directory, not a RESET target.
    root.mkdir(parents=True, exist_ok=False)
    event_file = root / "events.jsonl"
    script = Path(__file__).resolve()
    # Hooks use Git Bash on this installation: quote slash-form paths explicitly.
    hook_command = " ".join('"' + part.replace("\\", "/") + '"'
                            for part in (sys.executable, str(script), "hook", str(event_file)))
    events = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
              "PostToolUse", "PostToolUseFailure", "Stop", "StopFailure", "SessionEnd"]
    settings = root / "settings.json"
    hook_settings = {event: [{"hooks": [{"type": "command",
                         "command": hook_command + (" --continue-stop-once" if event == "Stop" and stop_once else ""),
                         "timeout": 5}]}] for event in events}
    env = os.environ.copy()
    if with_joro:
        install = Path(os.environ["LOCALAPPDATA"]) / "Joro/keep-awake"
        manifest = json.loads((install / "manifest.json").read_text(encoding="utf-8"))
        env["JORO_QA_INSTALLED_HELPER"] = str(install / "scripts/windows/keep_awake.py")
        for event in ("UserPromptSubmit", "PreToolUse", "SessionEnd"):
            hook_settings[event].append({"hooks": [{"type": "command", "command": manifest["hook_command"], "timeout": 5}]})
    settings.write_bytes(json.dumps({"permissions": {"ask": ["Bash"]}, "hooks": hook_settings}).encode())
    python_path = sys.executable.replace("\\", "/")
    script_path = str(script).replace("\\", "/")
    event_path = str(event_file).replace("\\", "/")
    harmless = f'"{python_path}" "{script_path}" work "{event_path}"'
    command = [executable, "--print", "--input-format", "stream-json", "--output-format",
               "stream-json", "--verbose", "--include-hook-events", "--no-session-persistence",
               "--setting-sources", "", "--settings", str(settings), "--strict-mcp-config",
               "--mcp-config", '{"mcpServers":{}}', "--no-chrome", "--disable-slash-commands",
               "--permission-mode", "manual", "--permission-prompt-tool", "stdio", "--tools", "Bash",
               "--system-prompt", "You are a controlled QA client. Run exactly the command provided using Bash once, then answer PROBE_DONE. Do not call any other tool."]
    proc = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            creationflags=subprocess.CREATE_NO_WINDOW)
    incoming = queue.Queue()
    def pump(stream):
        try:
            for line in stream:
                incoming.put(line)
        finally:
            incoming.put(None)
    # Stderr is drained but never persisted: it can contain account/provider data.
    def drain(stream):
        for _ in stream:
            pass
    threading.Thread(target=pump, args=(proc.stdout,), daemon=True).start()
    threading.Thread(target=drain, args=(proc.stderr,), daemon=True).start()
    timeline = []
    permitted = 0
    outcome = "no-result"
    error_kind = None
    diagnostic = None
    def send(value):
        proc.stdin.write(json.dumps(value) + "\n")
        proc.stdin.flush()
    try:
        send({"type": "user", "session_id": str(uuid.uuid4()), "parent_tool_use_id": None,
              "message": {"role": "user", "content": f"Execute exactly this harmless command once: {harmless}"}})
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                line = incoming.get(timeout=1)
            except queue.Empty:
                if proc.poll() is not None:
                    break
                continue
            if line is None:
                break
            if len(line) > 200_000:
                outcome = "oversized-event-refused"
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            if kind == "system" and event.get("subtype") == "init":
                timeline.append({"event": "client_init", "time_ns": time.time_ns(),
                                 "tools": event.get("tools", [])})
            elif kind == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        timeline.append({"event": "client_tool_use", "time_ns": time.time_ns(),
                                         "tool": block.get("name"),
                                         "exact_command": block.get("input", {}).get("command") == harmless})
            elif kind == "control_request":
                request = event.get("request", {})
                if request.get("subtype") == "can_use_tool":
                    data = request.get("input", {})
                    name = request.get("tool_name")
                    permitted_command = name == "Bash" and data.get("command") == harmless and permitted == 0
                    timeline.append({"event": "permission_received", "time_ns": time.time_ns(),
                                     "tool": name, "exact_command": permitted_command})
                    time.sleep(1)
                    response = {"behavior": "deny", "message": "Only the exact controlled probe is permitted"}
                    if permitted_command and not deny:
                        permitted += 1
                        response = {"behavior": "allow", "updatedInput": data}
                    timeline.append({"event": "permission_answered", "time_ns": time.time_ns(),
                                     "behavior": response["behavior"]})
                    send({"type": "control_response", "response": {"subtype": "success",
                          "request_id": event["request_id"], "response": response}})
            elif kind == "result":
                outcome = "client-error" if event.get("is_error") else "client-completed"
                if event.get("is_error"):
                    raw = json.dumps({key: event.get(key) for key in ("result", "errors", "error")})
                    detail = raw.lower()
                    categories = (("quota", ("usage limit", "session limit", "limit reached", "out of extra usage", "credit balance", "insufficient credits")),
                                  ("authentication", ("not logged in", "authentication", "invalid api key", "login", "oauth", "api key")),
                                  ("rate-limit", ("rate limit", "rate_limit", "429")),
                                  ("tool-configuration", ("unknown tool", "invalid tool", "powershell")),
                                  ("budget", ("budget",)),
                                  ("provider", ("overloaded", "model not found", "connection", "api error")))
                    error_kind = next((label for label, words in categories if any(w in detail for w in words)), "unclassified-client-error")
                    diagnostic = re.sub(r"https?://[^\s\"']+", "[URL]", raw)
                    diagnostic = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", diagnostic)
                    diagnostic = re.sub(r"(?i)(bearer\s+|sk-|ghp_|gho_)[A-Za-z0-9_.-]+", "[credential]", diagnostic)[:500]
                timeline.append({"event": "client_result", "time_ns": time.time_ns(),
                                 "subtype": event.get("subtype"), "is_error": bool(event.get("is_error"))})
                break
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    hooks = []
    if event_file.exists():
        hooks = [json.loads(line) for line in event_file.read_text(encoding="utf-8").splitlines()]
    report = {"outcome": outcome, "exit_code": proc.returncode, "error_kind": error_kind,
              "answer_mode": "deny" if deny else "allow",
              "stop_continuation_control": stop_once,
              "installed_hooks_exercised": with_joro,
              "permitted_commands": permitted, "hooks": hooks, "timeline": timeline,
              "scope": "disposable-Claude-print-SDK-path-not-interactive-terminal",
              "global_settings_changed": False, "watcher_verified": False}
    (root / "report.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({"report": str(root / "report.json"), "outcome": outcome, "error_kind": error_kind,
                      "diagnostic": diagnostic, "permitted_commands": permitted,
                      "hook_events": [h["event"] for h in hooks], "timeline": timeline}))
    work_events = [h for h in hooks if h["event"] == "controlled_tool_started"]
    finished = [h for h in hooks if h["event"] == "controlled_tool_finished"]
    valid = outcome == "client-completed" and (permitted == 1 and len(work_events) == 1 and len(finished) == 1
            if not deny else permitted == 0 and not work_events)
    if with_joro and not deny:
        valid = valid and any(h["event"] == "installed_claude_claim" and h["present"] for h in hooks)
    if stop_once:
        stops = [h for h in hooks if h["event"] == "Stop"]
        valid = valid and len(stops) == 2 and stops[0]["stop_hook_active"] is False and stops[1]["stop_hook_active"] is True
    return 0 if valid else 1


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "hook":
        raise SystemExit(capture_hook(Path(sys.argv[2]), continue_stop_once="--continue-stop-once" in sys.argv[3:]))
    if len(sys.argv) == 3 and sys.argv[1] == "work":
        raise SystemExit(controlled_work(Path(sys.argv[2])))
    raise SystemExit(run(deny="--deny" in sys.argv[1:], stop_once="--stop-once" in sys.argv[1:],
                         with_joro="--with-joro" in sys.argv[1:]))
