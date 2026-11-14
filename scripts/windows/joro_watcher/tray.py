"""Independent tray observer: never derives activity from open application windows."""

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from joro_watcher.event_log import record


def presentation(value):
    if value.get("error"):
        return "warning", "Joro: warning - " + value["error"]
    if value.get("diagnostic_error"):
        return "warning", "Joro: warning - " + value["diagnostic_error"]
    if not value.get("running"):
        return "warning", "Joro: monitoring stopped - sleep allowed"
    if value.get("uncertain_claims"):
        return "warning", "Joro: activity uncertain - keeping awake conservatively"
    if value.get("power_requested"):
        names = {"claude": "Claude Code", "opencode": "OpenCode"}
        clients = ", ".join(names.get(c, c) for c in value.get("clients", []))
        return "awake", "Joro: keeping awake" + (": " + clients if clients else "")
    return "idle", "Joro: idle - sleep allowed"


def observe(helper):
    """Read the helper's own report; unlike status(), do not reconcile claims."""
    try:
        value = json.loads((helper.ROOT / "helper.json").read_text(encoding="utf-8"))
        if helper.birth(value["pid"]) != value["birth"]:
            return {"running": False}
        if time.time() - value["updated_at"] > 10:
            return {"error": "helper is not reporting"}
        return {**value, "running": True}
    except FileNotFoundError:
        error = helper.ROOT / "helper-error.json"
        if error.exists():
            return {"error": "helper failed; see ~/.joro/keep-awake.log"}
        return {"running": False}
    except (OSError, ValueError, KeyError, TypeError):
        return {"error": "cannot read helper status"}


def images():
    from PIL import Image, ImageDraw, ImageFont
    result = {}
    for name in ("idle", "awake", "warning"):
        image = Image.new("RGBA", (64, 64))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((2, 2, 62, 62), radius=14,
                               fill={"idle": "#334155", "awake": "#047857", "warning": "#92400e"}[name])
        if name == "awake":
            draw.ellipse((9, 20, 55, 44), fill="white")
            draw.ellipse((24, 23, 40, 41), fill="#064e3b")
        elif name == "warning":
            draw.polygon(((32, 9), (57, 53), (7, 53)), fill="#fef3c7")
            draw.line((32, 23, 32, 36), fill="#92400e", width=5)
            draw.ellipse((30, 42, 34, 46), fill="#92400e")
        else:
            font = ImageFont.load_default(size=23)
            draw.text((6, 18), "Zzz", fill="white", font=font)
        result[name] = image
    return result


def stop_helper(helper):
    result = subprocess.run([sys.executable, str(Path(helper.__file__).resolve()), "stop"],
                            capture_output=True, text=True, timeout=10,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    value = json.loads(result.stdout)
    if value.get("running") is not False:
        raise RuntimeError("Helper shutdown was not confirmed")


def update(icon, icons, value):
    state, title = presentation(value)
    icon.icon, icon.title = icons[state], title[:127]
    return state, title


def exit_monitoring(helper, icon, icons, stopped, failure):
    try:
        stop_helper(helper)
    except Exception as exc:
        failure["error"] = "could not stop helper; retry Exit"
        update(icon, icons, failure)
        record("exit_failed", source="tray", error=str(exc))
        return False
    record("exit", source="tray")
    stopped.set()
    icon.stop()
    return True


def observe_once(helper, icon, icons, failure, previous):
    try:
        value = failure or observe(helper)
        state, title = presentation(value)
        signature = (state, title)
        if signature != previous:
            update(icon, icons, value)
            log_error = record("tray_state", state=state, detail=title)
            if log_error:
                update(icon, icons, {"error": log_error})
                return None  # Retry logging on the next tick.
        return signature
    except Exception as exc:
        # Never leave an eye frozen on screen after the observer has failed.
        try:
            update(icon, icons, {"error": "observer failed; retrying"})
        except Exception:
            pass  # A shell/UI failure is retried on the next observer tick too.
        record("observer_failed", source="tray", error=str(exc))
        return None


def run(helper):
    import pystray
    mutex = helper.K.CreateMutexW(None, False, "Local\\JoroTray-" + helper.KEY)
    if not mutex:
        raise OSError("Cannot create tray mutex")
    if helper.K.WaitForSingleObject(mutex, 0) not in (0, 0x80):
        helper.K.CloseHandle(mutex)
        return
    stopped = threading.Event()
    exit_event = helper.named_event("-tray-exit")
    helper.K.ResetEvent(exit_event)
    icons = images()
    icon = pystray.Icon("Joro", icons["warning"], "Joro: starting",
                        menu=pystray.Menu(pystray.MenuItem("Exit", lambda: exit_monitoring(
                            helper, icon, icons, stopped, failure))))
    failure = {}

    def monitor():
        previous = None
        while not stopped.is_set():
            if helper.K.WaitForSingleObject(exit_event, 0) == 0:
                record("exit", source="tray", reason="command")
                stopped.set()
                icon.stop()
                return
            previous = observe_once(helper, icon, icons, failure, previous)
            stopped.wait(1)

    thread = threading.Thread(target=monitor, name="joro-tray-observer", daemon=True)
    try:
        record("start", source="tray", pid=os.getpid())
        def setup(ready_icon):
            try:
                ready_icon.visible = True
                helper.write(helper.ROOT / "tray.json", {"pid": os.getpid(), "birth": helper.birth(os.getpid())})
                thread.start()
                ready = helper.named_event("-tray-ready")
                try:
                    helper.K.SetEvent(ready)
                finally:
                    helper.K.CloseHandle(ready)
            except Exception as exc:
                record("tray_setup_failed", source="tray", error=str(exc))
                stopped.set()
                icon.stop()
        icon.run(setup=setup)
    finally:
        stopped.set()
        if thread.ident is not None:
            thread.join(timeout=3)
        (helper.ROOT / "tray.json").unlink(missing_ok=True)
        helper.K.ReleaseMutex(mutex)
        helper.K.CloseHandle(mutex)
        helper.K.CloseHandle(exit_event)
