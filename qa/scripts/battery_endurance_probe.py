"""Coordinated, unchanged-policy DC/locked observation. Never locks or sleeps the PC."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import bench

sys.path.insert(0, str(bench.REPO / "scripts/windows"))
from joro_watcher.power import PowerRequest


class SystemPowerStatus(ctypes.Structure):
    _fields_ = [("ac", wintypes.BYTE), ("flags", wintypes.BYTE),
                ("percent", wintypes.BYTE), ("saver", wintypes.BYTE),
                ("remaining", wintypes.DWORD), ("full", wintypes.DWORD)]


class SessionInfo(ctypes.Structure):
    _fields_ = [("session", wintypes.ULONG), ("connection", ctypes.c_int),
                ("flags", wintypes.LONG), ("station", wintypes.WCHAR * 33),
                ("user", wintypes.WCHAR * 21), ("domain", wintypes.WCHAR * 18),
                ("logon", ctypes.c_longlong), ("connect", ctypes.c_longlong),
                ("disconnect", ctypes.c_longlong), ("last_input", ctypes.c_longlong),
                ("current", ctypes.c_longlong), ("in_bytes", wintypes.DWORD),
                ("out_bytes", wintypes.DWORD), ("in_frames", wintypes.DWORD),
                ("out_frames", wintypes.DWORD), ("in_compressed", wintypes.DWORD),
                ("out_compressed", wintypes.DWORD)]


class SessionData(ctypes.Union):
    _fields_ = [("info", SessionInfo)]


class SessionInfoEx(ctypes.Structure):
    _fields_ = [("level", wintypes.DWORD), ("data", SessionData)]


class Host:
    def __init__(self):
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.w = ctypes.WinDLL("wtsapi32", use_last_error=True)
        self.k.GetSystemPowerStatus.argtypes = [ctypes.POINTER(SystemPowerStatus)]
        self.k.GetSystemPowerStatus.restype = wintypes.BOOL
        self.k.WTSGetActiveConsoleSessionId.argtypes = []
        self.k.WTSGetActiveConsoleSessionId.restype = wintypes.DWORD
        self.k.GetTickCount64.argtypes = []
        self.k.GetTickCount64.restype = ctypes.c_ulonglong
        base = ctypes.WinDLL("kernelbase", use_last_error=True)
        self.clock = getattr(self.k, "QueryUnbiasedInterruptTimePrecise", None)
        if self.clock is None:
            self.clock = getattr(base, "QueryUnbiasedInterruptTimePrecise", None)
        self.precise_clock = self.clock is not None
        if self.clock is None:
            self.clock = self.k.QueryUnbiasedInterruptTime
        self.clock.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]
        self.clock.restype = None if self.precise_clock else wintypes.BOOL
        self.w.WTSQuerySessionInformationW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
            ctypes.c_int, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
        self.w.WTSQuerySessionInformationW.restype = wintypes.BOOL
        self.w.WTSFreeMemory.argtypes = [ctypes.c_void_p]
        self.w.WTSFreeMemory.restype = None

    def sample(self):
        power = SystemPowerStatus()
        if not self.k.GetSystemPowerStatus(ctypes.byref(power)):
            raise ctypes.WinError(ctypes.get_last_error())
        session = self.k.WTSGetActiveConsoleSessionId()
        if session == 0xFFFFFFFF:
            raise RuntimeError("No active physical console session")
        buffer, size = ctypes.c_void_p(), wintypes.DWORD()
        if not self.w.WTSQuerySessionInformationW(None, session, 25, ctypes.byref(buffer), ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if size.value < ctypes.sizeof(SessionInfoEx):
                raise RuntimeError("Unexpected WTS structure size")
            info = ctypes.cast(buffer, ctypes.POINTER(SessionInfoEx)).contents
            if info.level != 1 or info.data.info.flags not in (0, 1):
                raise RuntimeError("Console lock state unknown")
            locked = info.data.info.flags == 0
        finally:
            self.w.WTSFreeMemory(buffer)
        awake = ctypes.c_ulonglong()
        clock_result = self.clock(ctypes.byref(awake))
        if not self.precise_clock and not clock_result:
            raise ctypes.WinError(ctypes.get_last_error())
        return {"utc_ns": time.time_ns(), "uptime_s": self.k.GetTickCount64() / 1000,
                "awake_s": awake.value / 10_000_000, "console_session": session,
                "ac": int(power.ac), "battery_percent": int(power.percent),
                "critical_battery": bool(power.flags != 255 and power.flags & 4),
                "locked": locked}


def sleep_timeouts():
    command = ["powercfg", "/query", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError("Cannot read current Windows sleep policy")
    values = re.findall(r"0x([0-9a-fA-F]+)", result.stdout)
    if len(values) < 2:
        raise RuntimeError("Cannot decode current sleep-policy indices")
    return {"ac_seconds": int(values[-2], 16), "dc_seconds": int(values[-1], 16)}


def evaluate(samples, duration):
    if len(samples) < 2:
        return {"observation_passed": False, "reason": "insufficient-samples",
                "causal_attribution_verified": False, "watcher_verified": False}
    first, last = samples[0], samples[-1]
    elapsed = last["uptime_s"] - first["uptime_s"]
    awake = last["awake_s"] - first["awake_s"]
    gaps = [b["uptime_s"] - a["uptime_s"] for a, b in zip(samples, samples[1:])]
    conditions = all(s["ac"] == 0 and s["locked"] and not s["critical_battery"]
                     and s["console_session"] == first["console_session"] for s in samples)
    # Bounds describe this one-second-workload test, not an activity heuristic.
    passed = conditions and elapsed >= duration and abs(elapsed - awake) < 1 and max(gaps) < 5
    return {"observation_passed": passed, "elapsed_seconds": elapsed,
            "awake_seconds": awake, "suspend_estimate_seconds": max(0, elapsed - awake),
            "max_sample_gap_seconds": max(gaps), "conditions_held": conditions,
            "criteria": "DC+locked throughout; >=target duration; timer delta <1s; sample gaps <5s",
            "causal_attribution_verified": False, "watcher_verified": False}


def save(path: Path, data):
    encoded = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def run(coordinated: bool):
    host = Host()
    initial, policy = host.sample(), sleep_timeouts()
    if not coordinated:
        print(json.dumps({"host": initial, "sleep_policy": policy,
                          "mode": "read-only-preflight", "native_requests_held": False}))
        return 0
    if policy["dc_seconds"] != 600:
        raise RuntimeError("DC sleep timeout differs from the coordinated 600 seconds; re-plan duration")
    root = bench.base_directory() / bench.PROJECT / ("endurance-" + uuid.uuid4().hex[:12])
    root.mkdir(parents=True, exist_ok=False)
    target = policy["dc_seconds"] + 300 + 60
    status = {"stage": "waiting-for-unplug-and-lock", "policy": policy,
              "target_seconds": target, "display_required": False,
              "mode": "system-and-execution-only", "directory": str(root)}
    save(root / "status.json", status)
    print(json.dumps(status), flush=True)
    samples, reason, handle = [], "arm-timeout", None
    request, failure, cleanup_error, handle_closed = None, None, None, None
    try:
        request = PowerRequest("Joro QA coordinated battery/locked observation")
        handle = request.handle
        request.acquire()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            value = host.sample()
            if value["critical_battery"]:
                reason = "critical-battery-abort"
                break
            if value["ac"] == 0 and value["locked"]:
                samples.append(value)
                reason = "running"
                break
            time.sleep(1)
        if samples:
            save(root / "status.json", {**status, "stage": "running", "start": samples[0]})
            with (root / "samples.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(samples[0]) + "\n")
                stream.flush()
                while samples[-1]["uptime_s"] - samples[0]["uptime_s"] < target:
                    time.sleep(1)
                    value = host.sample()
                    samples.append(value)
                    stream.write(json.dumps(value) + "\n")
                    stream.flush()
                    if (value["ac"] != 0 or not value["locked"] or value["critical_battery"]
                            or value["console_session"] != samples[0]["console_session"]):
                        reason = "conditions-changed"
                        break
                else:
                    reason = "target-reached"
    except Exception as exc:
        reason = "probe-error"
        failure = {"type": type(exc).__name__, "winerror": getattr(exc, "winerror", None)}
    finally:
        if request is not None:
            try:
                request.close()
            except Exception as exc:
                cleanup_error = {"type": type(exc).__name__, "winerror": getattr(exc, "winerror", None)}
            try:
                handle_closed = not request.api.is_valid(handle)
            except OSError:
                handle_closed = None
        save(root / "cleanup.json", {"handle_closed": handle_closed, "error": cleanup_error,
              "remaining_owned_counts": request.acquired if request is not None else []})
    try:
        unchanged = sleep_timeouts() == policy
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        unchanged = False
    report = {**status, "stage": "finished", "stop_reason": reason,
              **evaluate(samples, target), "sample_count": len(samples),
              "policy_unchanged": unchanged, "probe_error": failure,
              "cleanup_error": cleanup_error, "native_handle_closed": handle_closed,
              "external_inhibitors_excluded": False}
    if (not unchanged or reason != "target-reached" or handle_closed is not True
            or failure is not None or cleanup_error is not None):
        report["observation_passed"] = False
    save(root / "report.json", report)
    save(root / "status.json", {"stage": "finished", "report": str(root / "report.json")})
    print(json.dumps({"report": str(root / "report.json"), **report}), flush=True)
    return 0 if report["observation_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinated", action="store_true",
                        help="Arm only after the operator agrees to unplug and lock; no forced lock/sleep")
    args = parser.parse_args()
    raise SystemExit(run(args.coordinated))
