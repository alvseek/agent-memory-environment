"""Metadata-only Claude hook capture. Drafting never activates hooks or clients."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import errno
import json
from pathlib import Path
import re
import sys
import time
import uuid

MAX_INPUT = 1024 * 1024
MAX_OUTPUT = 32768
MAX_ITEMS = 32
ATOM = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
EVENTS = (
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
    "PostToolUse", "PostToolUseFailure", "Notification", "SubagentStart",
    "SubagentStop", "TaskCreated", "TaskCompleted", "Stop", "StopFailure", "SessionEnd",
)
IDENTIFIERS = ("session_id", "prompt_id", "tool_use_id", "agent_id", "task_id")
LABELS = ("notification_type", "tool_name", "source", "permission_mode")
FLAGS = ("stop_hook_active", "is_interrupt")


def project(value: dict) -> dict:
    """Record only known metadata; absence and invalidity stay distinguishable."""
    if not isinstance(value, dict) or value.get("hook_event_name") not in EVENTS:
        raise ValueError("Unsupported hook input")
    result = {
        "schema": 1, "received_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns(),
        "capture_id": uuid.uuid4().hex, "event": value["hook_event_name"],
        "present_fields": [], "invalid_fields": [],
    }

    def atom(source, target, field, path):
        item = source.get(field)
        if item is None:
            target[field] = None
        elif isinstance(item, str) and ATOM.fullmatch(item):
            target[field] = item
        else:
            target[field] = None
            result["invalid_fields"].append(path)

    for name in (*IDENTIFIERS, *LABELS, *FLAGS, "background_tasks", "session_crons"):
        if name not in value:
            continue
        result["present_fields"].append(name)
        if name in (*IDENTIFIERS, *LABELS):
            atom(value, result, name, name)
        elif name in FLAGS:
            if type(value[name]) is bool:
                result[name] = value[name]
            else:
                result[name] = None
                result["invalid_fields"].append(name)
        else:
            items = value[name]
            if not isinstance(items, list):
                result[name] = None
                result["invalid_fields"].append(name)
                continue
            result[name + "_total"] = len(items)
            result[name + "_clipped"] = len(items) > MAX_ITEMS
            projected = []
            for index, item in enumerate(items[:MAX_ITEMS]):
                if not isinstance(item, dict):
                    projected.append(None)
                    result["invalid_fields"].append(f"{name}.{index}")
                    continue
                entry = {}
                # Never retain descriptions, commands, cron prompts or schedules.
                for field in (("id", "type", "status") if name == "background_tasks" else ("id",)):
                    if field in item:
                        atom(item, entry, field, f"{name}.{index}.{field}")
                projected.append(entry)
            result[name] = projected
    return result


def capture(stream, directory: Path) -> Path:
    """One atomic file per callback; timestamps are receipt order, not causality."""
    if not directory.is_dir() or any(
        part.is_symlink() or part.is_junction() for part in (directory, *directory.parents)
    ):
        raise ValueError("Capture directory must exist and have no linked ancestors")
    raw = stream.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        raise ValueError("Hook input exceeds capture bound")
    result = project(json.loads(raw))
    encoded = (json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(encoded) > MAX_OUTPUT:
        raise ValueError("Projected record exceeds capture bound")
    target = directory / f"{result['received_ns']}-{result['capture_id']}.json"
    temporary = target.with_suffix(".pending")
    try:
        with temporary.open("xb") as output:
            output.write(encoded)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def settings(directory: Path) -> dict:
    # Shell form works with the affected build's existing Git Bash hook runner.
    command = " ".join(
        '"' + str(part).replace("\\", "/") + '"'
        for part in (sys.executable, Path(__file__).resolve(), "capture", directory)
    )
    if any(character in command for character in ("\n", "\r", "$", "`")):
        raise ValueError("Hook path requires explicit quoting review")
    return {"hooks": {
        event: [{"hooks": [{"type": "command", "command": command, "timeout": 5}]}]
        for event in EVENTS
    }}


def draft(directory: Path) -> dict:
    directory = directory.absolute()
    events = directory / "events"
    config = settings(events)
    path = directory / "settings.draft.json"
    if ".." in directory.parts or any(
        part.is_symlink() or part.is_junction() for part in (directory, *directory.parents)
    ):
        raise ValueError("Draft destination must have no linked ancestors or parent traversal")

    def remove_if_empty(folder):
        try:
            folder.rmdir()
        except OSError as exc:
            if exc.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                raise

    with ExitStack() as rollback:
        for folder in (*reversed(directory.parents), directory, events):
            if folder in directory.parents and folder.is_dir():
                continue
            folder.mkdir()
            rollback.callback(remove_if_empty, folder)
        with path.open("x", encoding="utf-8", newline="\n") as out:
            rollback.callback(path.unlink)
            json.dump(config, out, indent=2)
            out.write("\n")
        rollback.pop_all()
    return {"draft": str(path), "events": str(events), "activated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("draft", "capture"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "draft":
            print(json.dumps(draft(args.directory)))
        else:
            capture(sys.stdin.buffer, args.directory)
        return 0
    except Exception as exc:
        # Exception messages may contain source JSON, paths or secrets.
        print(f"Claude signal capture failed ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
