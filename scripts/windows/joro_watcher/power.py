"""Owned native power requests; does not modify Windows power policy."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os

DISPLAY_REQUIRED = 0
SYSTEM_REQUIRED = 1
EXECUTION_REQUIRED = 3


class DetailedReason(ctypes.Structure):
    _fields_ = [("module", wintypes.HANDLE), ("reason_id", wintypes.ULONG),
                ("string_count", wintypes.ULONG),
                ("strings", ctypes.POINTER(wintypes.LPWSTR))]


class ReasonValue(ctypes.Union):
    _fields_ = [("detailed", DetailedReason), ("simple", wintypes.LPWSTR)]


class ReasonContext(ctypes.Structure):
    _fields_ = [("version", wintypes.ULONG), ("flags", wintypes.DWORD),
                ("reason", ReasonValue)]


class NativePowerAPI:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Joro native power requests require Windows")
        self.dll = ctypes.WinDLL("kernel32", use_last_error=True)
        declarations = (
            ("PowerCreateRequest", [ctypes.POINTER(ReasonContext)], wintypes.HANDLE),
            ("PowerSetRequest", [wintypes.HANDLE, ctypes.c_int], wintypes.BOOL),
            ("PowerClearRequest", [wintypes.HANDLE, ctypes.c_int], wintypes.BOOL),
            ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
            ("GetHandleInformation", [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        )
        for name, args, result in declarations:
            fn = getattr(self.dll, name)
            fn.argtypes, fn.restype = args, result

    def create(self, context: ReasonContext):
        handle = self.dll.PowerCreateRequest(ctypes.byref(context))
        if handle in (None, ctypes.c_void_p(-1).value):
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def set(self, handle, kind: int) -> None:
        if not self.dll.PowerSetRequest(handle, kind):
            raise ctypes.WinError(ctypes.get_last_error())

    def clear(self, handle, kind: int) -> None:
        if not self.dll.PowerClearRequest(handle, kind):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self, handle) -> None:
        if not self.dll.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def is_valid(self, handle) -> bool:
        flags = wintypes.DWORD()
        if self.dll.GetHandleInformation(handle, ctypes.byref(flags)):
            return True
        error = ctypes.get_last_error()
        if error == 6:  # ERROR_INVALID_HANDLE; other failures are not proof of closure.
            return False
        raise ctypes.WinError(error)


class PowerRequest:
    """One owner's handle and request counts; use from one supervising thread."""

    def __init__(self, reason: str = "Joro agent work is active", *, api=None):
        if not reason or "\0" in reason:
            raise ValueError("A nonempty, NUL-free request reason is required")
        self.api = api if api is not None else NativePowerAPI()
        self.context = ReasonContext(version=0, flags=1)
        self.context.reason.simple = reason
        self.handle = self.api.create(self.context)
        self.acquired: list[int] = []

    def acquire(self, *, display: bool = False) -> None:
        if self.handle is None:
            raise RuntimeError("Cannot acquire a closed request")
        kinds = [SYSTEM_REQUIRED, EXECUTION_REQUIRED]
        if display:
            kinds.append(DISPLAY_REQUIRED)
        for kind in kinds:
            if kind not in self.acquired:
                self.api.set(self.handle, kind)
                self.acquired.append(kind)

    def release(self) -> None:
        errors = []
        for kind in reversed(self.acquired.copy()):
            try:
                self.api.clear(self.handle, kind)
                self.acquired.remove(kind)
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup("Some native requests could not be cleared", errors)

    def close(self) -> None:
        if self.handle is None:
            return
        errors = []
        try:
            self.release()
        except ExceptionGroup as exc:
            errors.extend(exc.exceptions)
        try:
            self.api.close(self.handle)
            self.handle = None
            self.acquired.clear()
        except OSError as exc:
            errors.append(exc)
        if errors:
            raise ExceptionGroup("Native power-request cleanup failed", errors)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except ExceptionGroup as cleanup:
            if exc is not None:
                raise BaseExceptionGroup("Request operation and cleanup failed", [exc, cleanup]) from None
            raise
        return False
