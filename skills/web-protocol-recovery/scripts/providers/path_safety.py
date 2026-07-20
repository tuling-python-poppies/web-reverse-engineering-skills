#!/usr/bin/env python3
"""Hold plain filesystem objects open while a provider validates or writes them."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any


FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def absolute_no_resolve(path: Path) -> Path:
    return Path(os.path.abspath(path))


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def ensure_plain_path(path: Path) -> None:
    path = absolute_no_resolve(path)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() or is_reparse_point(current):
            raise ValueError(f"reparse path is not allowed: {current}")


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _create_file = _kernel32.CreateFileW
    _create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _create_file.restype = wintypes.HANDLE
    _get_file_information = _kernel32.GetFileInformationByHandle
    _get_file_information.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation)]
    _get_file_information.restype = wintypes.BOOL
    _close_handle = _kernel32.CloseHandle
    _close_handle.argtypes = [wintypes.HANDLE]
    _close_handle.restype = wintypes.BOOL

    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    _FILE_READ_ATTRIBUTES = 0x80
    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x1
    _FILE_SHARE_WRITE = 0x2
    _OPEN_EXISTING = 3
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000


class PlainPathGuard:
    """Prevent checked path components from being replaced during an operation."""

    def __init__(self) -> None:
        self._locked: dict[str, tuple[str, Any]] = {}

    def __enter__(self) -> "PlainPathGuard":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        for kind, handle in reversed(list(self._locked.values())):
            if kind == "win":
                _close_handle(handle)
            else:
                os.close(int(handle))
        self._locked.clear()

    def _entry(self, path: Path):
        base = os.path.normcase(str(absolute_no_resolve(path)))
        return self._locked.get(base + ":delete") or self._locked.get(base + ":inspect")

    def _lock_one(self, path: Path, *, directory: bool, protect_delete: bool = False) -> None:
        path = absolute_no_resolve(path)
        key = os.path.normcase(str(path)) + (":delete" if protect_delete else ":inspect")
        if key in self._locked:
            return
        if path.is_symlink() or is_reparse_point(path):
            raise ValueError(f"reparse path is not allowed: {path}")

        if os.name == "nt":
            handle = _create_file(
                str(path),
                _FILE_READ_ATTRIBUTES | _GENERIC_READ,
                _FILE_SHARE_READ | _FILE_SHARE_WRITE,
                None,
                _OPEN_EXISTING,
                _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
                None,
            )
            if handle == _INVALID_HANDLE_VALUE:
                raise ctypes.WinError(ctypes.get_last_error(), f"could not lock path: {path}")
            info = _ByHandleFileInformation()
            if not _get_file_information(handle, ctypes.byref(info)):
                error = ctypes.WinError(ctypes.get_last_error(), f"could not inspect path: {path}")
                _close_handle(handle)
                raise error
            is_directory = bool(info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
            if info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
                _close_handle(handle)
                raise ValueError(f"reparse path is not allowed: {path}")
            if is_directory != directory:
                _close_handle(handle)
                expected = "directory" if directory else "regular file"
                raise ValueError(f"expected {expected}: {path}")
            if not directory and info.nNumberOfLinks != 1:
                _close_handle(handle)
                raise ValueError(f"hard-linked file is not allowed: {path}")
            self._locked[key] = ("win", handle)
            return

        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        if directory:
            flags |= getattr(os, "O_DIRECTORY", 0)
        else:
            flags |= getattr(os, "O_NONBLOCK", 0)
        parent_entry = self._entry(path.parent)
        if parent_entry and parent_entry[0] == "fd" and path.parent != path:
            descriptor = os.open(path.name, flags, dir_fd=int(parent_entry[1]))
        else:
            descriptor = os.open(path, flags)
        stat_result = os.fstat(descriptor)
        valid_type = stat.S_ISDIR(stat_result.st_mode) if directory else stat.S_ISREG(stat_result.st_mode)
        if not valid_type:
            os.close(descriptor)
            expected = "directory" if directory else "regular file"
            raise ValueError(f"expected {expected}: {path}")
        if not directory and stat_result.st_nlink != 1:
            os.close(descriptor)
            raise ValueError(f"hard-linked file is not allowed: {path}")
        self._locked[key] = ("fd", descriptor)

    def directory_fd(self, path: Path) -> int:
        if os.name == "nt":
            raise OSError("directory file descriptors are unavailable on Windows")
        entry = self._entry(path)
        if entry is None or entry[0] != "fd" or not stat.S_ISDIR(os.fstat(int(entry[1])).st_mode):
            raise ValueError(f"directory is not locked: {path}")
        return int(entry[1])

    def verify_directory(self, path: Path) -> None:
        if os.name == "nt":
            return
        descriptor = self.directory_fd(path)
        expected = os.fstat(descriptor)
        current = os.stat(path, follow_symlinks=False)
        if (expected.st_dev, expected.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError(f"checked directory was replaced: {path}")

    def read_bytes(self, path: Path) -> bytes:
        self.lock_file(path)
        if os.name == "nt":
            return absolute_no_resolve(path).read_bytes()
        entry = self._entry(path)
        if entry is None or entry[0] != "fd":
            raise ValueError(f"file is not locked: {path}")
        descriptor = int(entry[1])
        chunks = []
        offset = 0
        while True:
            chunk = os.pread(descriptor, 1024 * 1024, offset)
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
        return b"".join(chunks)

    def read_text(self, path: Path, *, encoding: str = "utf-8") -> str:
        return self.read_bytes(path).decode(encoding)

    def lock_directory(self, path: Path, *, require_exists: bool = True) -> None:
        path = absolute_no_resolve(path)
        current = Path(path.anchor)
        components = [current]
        for part in path.parts[1:]:
            current /= part
            components.append(current)
        for index, component in enumerate(components):
            if component.is_symlink() or is_reparse_point(component):
                raise ValueError(f"reparse path is not allowed: {component}")
            if not component.exists():
                if require_exists:
                    raise ValueError(f"expected directory: {path}")
                break
            self._lock_one(component, directory=True, protect_delete=index == len(components) - 1)

    def lock_file(self, path: Path) -> None:
        path = absolute_no_resolve(path)
        self.lock_directory(path.parent)
        self._lock_one(path, directory=False)

    def lock_existing(self, path: Path) -> None:
        path = absolute_no_resolve(path)
        if path.is_symlink() or is_reparse_point(path):
            raise ValueError(f"reparse path is not allowed: {path}")
        if path.is_dir():
            self.lock_directory(path)
        elif path.is_file():
            self.lock_file(path)
        else:
            raise ValueError(f"expected filesystem object: {path}")
