"""Install only Joro's small local helper, adapters and lifecycle skill."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import venv

SOURCE = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ["LOCALAPPDATA"]) / "Joro/keep-awake"
OPENCODE = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "opencode"
CLAUDE = Path.home() / ".claude/settings.json"
MANIFEST = INSTALL / "manifest.json"
UNCHECKED = object()
FILES = ("scripts/windows/keep_awake.py", "scripts/windows/joro_watcher/__init__.py",
          "scripts/windows/joro_watcher/power.py", "integrations/opencode/index.js",
          "scripts/windows/joro_watcher/tray.py", "scripts/windows/joro_watcher/event_log.py",
          "procedures/keep-awake.md", "setup-scripts/install_keep_awake.py")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace(path, data, before=UNCHECKED):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_bytes(data)
    if before is not UNCHECKED and ((before is None and path.exists()) or
            (before is not None and (not path.exists() or path.read_bytes() != before))):
        temporary.unlink()
        raise RuntimeError(f"Concurrent edit detected; preserved {path}")
    temporary.replace(path)


def hooks(settings, old_command, new_command):
    result = json.loads(json.dumps(settings))
    if not isinstance(result, dict) or not isinstance(result.get("hooks", {}), dict):
        raise ValueError("Expected a settings object with hook groups")
    groups = result.setdefault("hooks", {})
    removable = {c for c in (old_command, new_command) if c}
    if removable:
        for event in list(groups):
            retained = []
            for group in groups[event]:
                if not any(h.get("command") in removable for h in group.get("hooks", [])):
                    retained.append(group)
                    continue
                callbacks = [h for h in group.get("hooks", []) if h.get("command") not in removable]
                if callbacks:
                    retained.append({**group, "hooks": callbacks})
            if retained:
                groups[event] = retained
            else:
                del groups[event]
    if new_command:
        for event in ("UserPromptSubmit", "PreToolUse", "Notification", "SessionEnd"):
            group = {"hooks": [{"type": "command", "command": new_command, "timeout": 5}]}
            if event == "Notification":
                group["matcher"] = "idle_prompt"
            groups.setdefault(event, []).append(group)
    if not groups:
        result.pop("hooks", None)
    return result


def edit_settings(old_command, new_command):
    before = CLAUDE.read_bytes() if CLAUDE.exists() else None
    original = json.loads(before.decode("utf-8-sig")) if before is not None else {}
    updated = hooks(original, old_command, new_command)
    if updated == original:
        return
    if before is not None:
        backup = INSTALL / "backups" / ("claude-settings-" + uuid.uuid4().hex + ".json")
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(before)
    replace(CLAUDE, (json.dumps(updated, indent=2, ensure_ascii=False) + "\n").encode(), before)


def install():
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    helper = INSTALL / "scripts/windows/keep_awake.py"
    # Validate existing settings before writing anything to them.
    if CLAUDE.exists():
        json.loads(CLAUDE.read_text(encoding="utf-8-sig"))
    environment = INSTALL / ".venv"
    if not (environment / "Scripts/python.exe").exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(environment / "Scripts/python.exe"), "-m", "pip", "install",
                    "pystray==0.19.5", "Pillow>=10.1,<13"], check=True,
                   stdout=sys.stderr)
    owned = {}
    def put(target, data):
        current = None
        if target.exists():
            current = target.read_bytes()
            old_hash = previous.get("files", {}).get(str(target))
            if current != data and digest(current) != old_hash:
                raise RuntimeError(f"Unowned/modified target; refusing overwrite: {target}")
        if current != data:
            replace(target, data, current)
        owned[str(target)] = digest(data)
    for name in FILES:
        put(INSTALL / name, (SOURCE / name).read_bytes())
    plugin = OPENCODE / "plugins/joro-keep-awake"
    put(plugin / "config.json", (json.dumps({"python": sys.executable, "helper": str(helper)}) + "\n").encode())
    put(plugin / "index.js", (SOURCE / "integrations/opencode/index.js").read_bytes())
    skill = (SOURCE / "procedures/keep-awake.md").read_text(encoding="utf-8")
    for key, value in {"[JORO-PYTHON]": sys.executable, "[JORO-HELPER]": str(helper),
                       "[JORO-INSTALLER]": str(INSTALL / "setup-scripts/install_keep_awake.py")}.items():
        skill = skill.replace(key, value)
    for directory in (Path.home() / ".claude/skills/joro-keep-awake", OPENCODE / "skills/joro-keep-awake"):
        put(directory / "SKILL.md", skill.encode("utf-8"))
    command = '"' + sys.executable.replace("\\", "/") + '" "' + str(helper).replace("\\", "/") + '" hook'
    edit_settings(previous.get("hook_command"), command)
    replace(MANIFEST, (json.dumps({"version": "0.1.0", "files": owned, "hook_command": command}, indent=2) + "\n").encode())
    print(json.dumps({"installed": str(INSTALL), "helper": str(helper),
                      "startup_enabled_by_install": False, "started_by_install": False}))


def uninstall():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    helper = INSTALL / "scripts/windows/keep_awake.py"
    current = subprocess.run([sys.executable, str(helper), "status"], capture_output=True, text=True, check=True)
    activity = json.loads(current.stdout)
    if activity["active_count"] or activity["uncertain_claims"]:
        raise RuntimeError("Close active Claude/OpenCode sessions first, then uninstall from a separate PowerShell window")
    subprocess.run([sys.executable, str(helper), "exit"], check=True)
    subprocess.run([sys.executable, str(helper), "startup-off"], check=True)
    edit_settings(manifest["hook_command"], None)
    preserved = []
    for name, expected in manifest["files"].items():
        path = Path(name)
        if path.exists():
            if digest(path.read_bytes()) == expected:
                path.unlink()
            else:
                preserved.append(name)
    if not preserved:
        MANIFEST.unlink()
    print(json.dumps({"uninstalled_owned_files": not preserved, "preserved_modified_files": preserved,
                      "backups_runtime_logs_and_environment_preserved": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    (uninstall if args.uninstall else install)()
