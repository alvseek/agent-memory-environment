"""Isolated, finite-probe QA rig. This is not the Joro watcher."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[2]
PROJECT = hashlib.sha256(str(REPO).casefold().encode()).hexdigest()[:12]
SCHEMA = 1
OWNED = {"run.json", "baseline.json", "ready.json", "result.json", "process.json",
         "stdout.log", "stderr.log"}
MARKER = ".joro-qa-root.json"
KERNEL = None


def kernel():
    global KERNEL
    if os.name != "nt":
        raise RuntimeError("This QA bench targets Windows only")
    if KERNEL is None:
        KERNEL = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("OpenProcess", [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ("GetProcessTimes", [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4, wintypes.BOOL),
            ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
            ("WaitForSingleObject", [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            ("TerminateProcess", [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            ("CreateMutexW", [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            ("ReleaseMutex", [wintypes.HANDLE], wintypes.BOOL),
            ("GetFileAttributesW", [wintypes.LPCWSTR], wintypes.DWORD),
        ):
            fn = getattr(KERNEL, name)
            fn.argtypes, fn.restype = args, result
    return KERNEL


def base_directory() -> Path:
    # Ask Windows, not HOME/LOCALAPPDATA supplied by a test process.
    kernel()
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    shell.SHGetFolderPathW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE,
                                       wintypes.DWORD, wintypes.LPWSTR]
    shell.SHGetFolderPathW.restype = ctypes.c_long
    buffer = ctypes.create_unicode_buffer(32768)
    if shell.SHGetFolderPathW(None, 0x1C, None, 0, buffer) != 0:
        raise RuntimeError("Cannot resolve Windows Local AppData")
    return Path(buffer.value) / "Temp" / "opencode" / "joro-qa"


def root_for(name: str) -> Path:
    if not re.fullmatch(r"default|test-[0-9a-f]{12}", name):
        raise ValueError("Sandbox name must be default or test-<12 hex digits>; no paths")
    return base_directory() / PROJECT / name


def check_path(root: Path) -> None:
    expected = root_for(root.name)
    if root != expected:
        raise RuntimeError("Refusing a target outside this project's QA namespace")
    for part in [root, *root.parents]:
        if part.exists():
            attrs = kernel().GetFileAttributesW(str(part))
            if attrs == 0xFFFFFFFF or attrs & 0x400:
                raise RuntimeError(f"Refusing unreadable/reparse path: {part}")


def read(root: Path, name: str) -> dict:
    check_path(root)
    path = root / name
    if path.is_symlink() or path.is_junction() or path.stat().st_nlink != 1:
        raise RuntimeError("Refusing a linked QA file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object: {name}")
    return value


def write(root: Path, name: str, value: dict) -> None:
    check_path(root)
    data = (json.dumps(value, indent=2) + "\n").encode("utf-8")
    temp = root / f".{name}.{uuid.uuid4().hex}.tmp"
    temp.write_bytes(data)
    temp.replace(root / name)


def marker() -> dict:
    return {"schema": SCHEMA, "project": PROJECT, "purpose": "joro-qa-only"}


def validate_root(root: Path) -> None:
    if read(root, MARKER) != marker():
        raise RuntimeError("Missing or mismatched QA ownership marker")
    for path in root.iterdir():
        if (not path.is_file() or path.is_symlink() or path.is_junction()
                or path.stat().st_nlink != 1):
            raise RuntimeError("Refusing linked/non-file QA content")


@contextlib.contextmanager
def lock(root: Path):
    check_path(root)
    key = hashlib.sha256(str(root).encode()).hexdigest()
    handle = kernel().CreateMutexW(None, False, "Local\\JoroQABench-" + key)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    acquired = False
    try:
        code = kernel().WaitForSingleObject(handle, 3000)
        if code not in (0, 0x80):
            raise RuntimeError("QA sandbox is busy or its lock is unavailable")
        acquired = True
        yield
    finally:
        if acquired:
            kernel().ReleaseMutex(handle)
        kernel().CloseHandle(handle)


def birth(handle) -> int:
    times = [wintypes.FILETIME() for _ in range(4)]
    if not kernel().GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
        raise ctypes.WinError(ctypes.get_last_error())
    return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime


@contextlib.contextmanager
def process_handle(pid: int, terminate: bool = False):
    if type(pid) is not int or pid <= 0 or pid == os.getpid():
        raise RuntimeError("Invalid bench child PID")
    rights = 0x1000 | 0x100000 | (1 if terminate else 0)
    handle = kernel().OpenProcess(rights, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # No such process; access denied is NOT proof of death.
            yield None
            return
        raise ctypes.WinError(error)
    try:
        yield handle
    finally:
        kernel().CloseHandle(handle)


def stop_child(root: Path) -> None:
    if not (root / "process.json").exists():
        return
    record = read(root, "process.json")
    run = read(root, "run.json")
    if (record.get("run_id") != run.get("run_id") or
            record.get("specimen") != "bench-self-smoke" or
            type(record.get("birth")) is not int):
        raise RuntimeError("Refusing unverified QA process ownership")
    with process_handle(record["pid"], terminate=True) as handle:
        if handle is None or birth(handle) != record["birth"]:
            return  # Gone or PID reused: do not signal the replacement.
        if kernel().WaitForSingleObject(handle, 0) == 0x102:
            if not kernel().TerminateProcess(handle, 1):
                raise ctypes.WinError(ctypes.get_last_error())
            if kernel().WaitForSingleObject(handle, 5000) != 0:
                raise RuntimeError("Bench child failed to exit")


def reset(root: Path) -> dict:
    check_path(root)
    if root.exists():
        validate_root(root)
        for path in root.iterdir():
            temporary = any(re.fullmatch(r"\." + re.escape(n) + r"\.[0-9a-f]{32}\.tmp", path.name)
                            for n in OWNED | {MARKER})
            if path.name not in OWNED | {MARKER} and not temporary:
                raise RuntimeError(f"Unexpected file; refusing reset: {path.name}")
            if not path.is_file() or path.is_symlink() or path.is_junction():
                raise RuntimeError("Refusing linked/non-file QA content")
        stop_child(root)
        for path in root.iterdir():
            if path.name != MARKER:
                path.unlink()  # Exact owned files only; never a recursive delete.
    else:
        root.mkdir(parents=True)
        write(root, MARKER, marker())
    write(root, "run.json", {"schema": SCHEMA, "run_id": uuid.uuid4().hex,
                             "created_ns": time.time_ns(), "stage": "reset"})
    return {"stage": "reset", "sandbox": str(root)}


def run_state(root: Path, stage: str) -> dict:
    validate_root(root)
    state = read(root, "run.json")
    if state.get("schema") != SCHEMA or state.get("stage") != stage:
        raise RuntimeError(f"Expected completed {stage} phase")
    if not re.fullmatch(r"[0-9a-f]{32}", state.get("run_id", "")):
        raise RuntimeError("Invalid run identity")
    return state


def inject(root: Path) -> dict:
    state = run_state(root, "reset")
    source = json.loads((REPO / "qa/seeds/baseline.json").read_text(encoding="utf-8"))
    if source != {"schema": 1, "specimen": "bench-self-smoke",
                  "message": "synthetic Joro QA input"}:
        raise RuntimeError("Unexpected seed; only the synthetic bench specimen is allowed")
    write(root, "baseline.json", {**source, "run_id": state["run_id"]})
    write(root, "run.json", {**state, "stage": "injected"})
    return {"stage": "injected", "seed": "dummy", "run_id": state["run_id"]}


def worker(root: Path, run_id: str) -> dict:
    state = run_state(root, "injected")
    baseline = read(root, "baseline.json")
    if state["run_id"] != run_id or baseline.get("run_id") != run_id:
        raise RuntimeError("Specimen run identity mismatch")
    write(root, "ready.json", {"schema": 1, "run_id": run_id, "pid": os.getpid(),
                               "ready_ns": time.time_ns()})
    # Handshake, not a guessed delay: do not exit before ACT records ownership.
    deadline = time.monotonic() + 5
    while not (root / "process.json").exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("Parent did not register specimen ownership")
        time.sleep(0.02)
    owner = read(root, "process.json")
    if owner.get("run_id") != run_id or owner.get("pid") != os.getpid():
        raise RuntimeError("Parent registered the wrong specimen")
    result = {"schema": 1, "run_id": run_id, "pid": os.getpid(), "ok": True,
              "completed_ns": time.time_ns(), "message": baseline["message"],
              "boundary": "bench-child-process-and-files", "watcher_verified": False,
              "battery_verified": False}
    write(root, "result.json", result)
    return result


def act(root: Path) -> dict:
    state = run_state(root, "injected")
    command = [sys.executable, str(Path(__file__).resolve()), "worker",
               "--sandbox", root.name, "--run-id", state["run_id"]]
    proc = None
    try:
        with (root / "stdout.log").open("wb") as out, (root / "stderr.log").open("wb") as err:
            proc = subprocess.Popen(command, stdout=out, stderr=err,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            with process_handle(proc.pid) as handle:
                if handle is None:
                    raise RuntimeError("Specimen exited before supervision attached")
                write(root, "process.json", {"schema": 1, "run_id": state["run_id"], "pid": proc.pid,
                                              "birth": birth(handle), "specimen": "bench-self-smoke"})
            exit_code = proc.wait(timeout=10)
        write(root, "run.json", {**state, "stage": "acted", "child_exit": exit_code})
        if exit_code:
            raise RuntimeError(f"Specimen exited with {exit_code}; inspect sandbox stderr.log")
        return {"stage": "acted", "run_id": state["run_id"], "child_exit": exit_code}
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def observe(root: Path) -> dict:
    state = run_state(root, "acted")
    ready, result, owner = (read(root, n) for n in ("ready.json", "result.json", "process.json"))
    for record in (ready, result, owner):
        if record.get("schema") != 1 or record.get("run_id") != state["run_id"]:
            raise RuntimeError("Stale/mismatched probe evidence")
    if not (ready.get("pid") == result.get("pid") == owner.get("pid")):
        raise RuntimeError("Probe owner mismatch")
    if not (type(ready.get("ready_ns")) is int and type(result.get("completed_ns")) is int
            and state["created_ns"] <= ready["ready_ns"] <= result["completed_ns"]):
        raise RuntimeError("Probe timestamps do not belong to this run")
    if (state.get("child_exit") != 0 or result.get("ok") is not True or
            result.get("boundary") != "bench-child-process-and-files" or
            result.get("message") != "synthetic Joro QA input" or
            result.get("watcher_verified") is not False or
            result.get("battery_verified") is not False):
        raise RuntimeError("Invalid or unsuccessful bench specimen result")
    with process_handle(owner["pid"]) as handle:
        if handle is not None and birth(handle) == owner["birth"]:
            if kernel().WaitForSingleObject(handle, 0) != 0:
                raise RuntimeError("Bench child remains running")
    return {"ok": True, "run_id": state["run_id"], "child_exited": True,
            "boundary": result["boundary"], "watcher_verified": False, "battery_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("reset", "inject", "act", "observe", "worker"))
    parser.add_argument("--sandbox", default="default")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        root = root_for(args.sandbox)
        # Worker is supervised by ACT, which already owns the sandbox mutex.
        if args.phase == "worker":
            value = worker(root, args.run_id)
        else:
            with lock(root):
                value = {"reset": reset, "inject": inject, "act": act, "observe": observe}[args.phase](root)
        print(json.dumps(value))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"QA {args.phase} failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
