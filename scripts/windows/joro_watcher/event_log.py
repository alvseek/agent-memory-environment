"""Bounded, process-safe lifecycle history; callers supply metadata, never content."""

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

LAST_ERROR = None


class StrictRotatingHandler(RotatingFileHandler):
    def handleError(self, entry):
        # logging normally prints and swallows these errors, which hides disk failures.
        raise


@contextmanager
def locked(name):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    acquired = False
    try:
        result = kernel.WaitForSingleObject(handle, 5000)
        if result not in (0, 0x80):
            raise RuntimeError("Timed out acquiring Joro log lock")
        acquired = True
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def _record(event, *, directory=None, **fields):
    """Open/close under one lock so no other process holds a rotated file open."""
    directory = Path(directory) if directory is not None else Path.home() / ".joro"
    key = hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()[:20]
    with locked("Local\\JoroLog-" + key):
        directory.mkdir(parents=True, exist_ok=True)
        handler = StrictRotatingHandler(directory / "keep-awake.log",
                                      maxBytes=1024 * 1024, backupCount=4, encoding="utf-8")
        try:
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            # Prevent one unexpectedly large error from defeating the file bound.
            message = json.dumps({"event": event, **fields}, ensure_ascii=True)
            if len(message) > 8192:
                message = json.dumps({"event": str(event)[:128], "truncated": True})
            entry = logging.LogRecord("joro", logging.INFO, "", 0, message, (), None)
            handler.emit(entry)
        finally:
            handler.close()


def record(event, *, directory=None, **fields):
    """Diagnostics must never release a power request or kill the observer."""
    global LAST_ERROR
    try:
        _record(event, directory=directory, **fields)
    except Exception as exc:
        LAST_ERROR = f"Cannot write Joro log: {type(exc).__name__}"
        try:
            print(LAST_ERROR, file=sys.stderr)
        except Exception:
            pass
        return LAST_ERROR
    LAST_ERROR = None
    return None
