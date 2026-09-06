"""Shared safety primitives for the GT4 delivery templates.

The templates must keep their request budget across process launches, reject
alias paths before writing captures, and never treat Node's vm module as a
security boundary. This module stays stdlib-only so its contract tests can run
offline without OCR or crypto dependencies.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qsl, urlparse


FILE_ATTRIBUTE_REPARSE_POINT = 0x400
BUDGET_KINDS = (
    "navigation",
    "request",
    "retry",
    "websocketHandshake",
    "websocketFrame",
)
LOT_NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
LEDGER_ID_RE = re.compile(r"[a-f0-9]{64}\Z")
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class BudgetError(RuntimeError):
    """Raised when a work-order budget cannot safely reserve another attempt."""


class SandboxError(RuntimeError):
    """Raised before unsafe local target-code execution can begin."""


def absolute_no_resolve(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def _reject_windows_alias_parts(path: Path) -> None:
    for part in path.parts[1:]:
        if not part or part in {".", ".."} or part.rstrip(". ") != part:
            raise ValueError(f"unsafe path component: {part!r}")


def ensure_plain_path(path: Path) -> Path:
    """Return an absolute path only after every existing component is plain."""
    path = absolute_no_resolve(path)
    _reject_windows_alias_parts(path)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            continue
        if current.is_symlink() or is_reparse_point(current):
            raise ValueError(f"reparse path is not allowed: {current}")
    return path


def ensure_plain_directory(path: Path, *, create: bool) -> Path:
    path = ensure_plain_path(path)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if os.path.lexists(current):
            if current.is_symlink() or is_reparse_point(current) or not current.is_dir():
                raise ValueError(f"expected plain directory: {current}")
            continue
        if not create:
            raise FileNotFoundError(f"directory does not exist: {current}")
        current.mkdir()
        if current.is_symlink() or is_reparse_point(current) or not current.is_dir():
            raise ValueError(f"new directory is not plain: {current}")
    return path


def ensure_plain_file(path: Path) -> Path:
    path = ensure_plain_path(path)
    if not path.is_file() or path.is_symlink() or is_reparse_point(path):
        raise ValueError(f"expected plain regular file: {path}")
    if os.stat(path, follow_symlinks=False).st_nlink != 1:
        raise ValueError(f"hard-linked file is not allowed: {path}")
    return path


def create_exclusive_directory(path: Path) -> Path:
    path = ensure_plain_path(path)
    ensure_plain_directory(path.parent, create=True)
    if os.path.lexists(path):
        raise FileExistsError(f"refusing to reuse cache directory: {path}")
    path.mkdir()
    return ensure_plain_directory(path, create=False)


def write_new_bytes(path: Path, payload: bytes) -> Path:
    path = ensure_plain_path(path)
    ensure_plain_directory(path.parent, create=False)
    if os.path.lexists(path):
        raise FileExistsError(f"refusing to overwrite artifact: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return ensure_plain_file(path)


def write_new_text(path: Path, payload: str) -> Path:
    return write_new_bytes(path, payload.encode("utf-8"))


def write_new_json(path: Path, payload: Any) -> Path:
    return write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    path = ensure_plain_file(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_plain_text(path: Path) -> str:
    return ensure_plain_file(path).read_text(encoding="utf-8")


def _relative_project_path(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"{label} must be a nonempty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} must be a contained relative path")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"{label} must not be drive-qualified")
    return path


def _project_path(project_root: Path, value: Any, label: str) -> Path:
    relative = _relative_project_path(value, label)
    return ensure_plain_path(project_root / Path(*relative.parts))


def _allowed_contains(project_root: Path, allowed_paths: Iterable[Any], target: Path) -> bool:
    for raw_path in allowed_paths:
        if not isinstance(raw_path, str) or not raw_path:
            continue
        if raw_path.endswith("/**"):
            base = _project_path(project_root, raw_path[:-3], "project.allowedPaths")
            try:
                target.relative_to(base)
            except ValueError:
                continue
            return True
        candidate = _project_path(project_root, raw_path, "project.allowedPaths")
        if target == candidate:
            return True
    return False


def validate_cache_root(project: Dict[str, Any], cache_root: Path) -> Path:
    project_root = Path(str(project.get("projectRoot") or ""))
    if not project_root.is_absolute():
        raise ValueError("project.projectRoot must be absolute")
    project_root = ensure_plain_directory(project_root, create=False)
    cache_root = cache_root if cache_root.is_absolute() else Path.cwd() / cache_root
    cache_root = ensure_plain_path(cache_root)
    try:
        cache_root.relative_to(project_root)
    except ValueError as error:
        raise ValueError("--cache-root must stay under project.projectRoot") from error
    allowed_paths = project.get("allowedPaths") or []
    cache_allowed = any(
        isinstance(raw_path, str)
        and raw_path.endswith("/**")
        and _allowed_contains(project_root, [raw_path], cache_root)
        for raw_path in allowed_paths
    )
    if not cache_allowed:
        raise ValueError("--cache-root must stay under a terminal /** allowedPaths entry")
    return cache_root


def safe_lot_cache(cache_root: Path, lot_number: Any) -> Path:
    """Build a contained cache directory from a server-controlled lot number."""
    lot = lot_number if isinstance(lot_number, str) else ""
    stem = lot.split(".", 1)[0].upper()
    if (
        not LOT_NAME_RE.fullmatch(lot)
        or lot in {".", ".."}
        or lot.rstrip(". ") != lot
        or stem in WINDOWS_RESERVED_NAMES
    ):
        raise ValueError(f"unsafe lot_number for cache path: {lot_number!r}")
    cache_root = ensure_plain_directory(cache_root, create=False)
    cache = ensure_plain_path(cache_root / lot)
    try:
        cache.relative_to(cache_root)
    except ValueError as error:
        raise ValueError(f"lot_number escapes cache root: {lot!r}") from error
    return cache


UNRESERVED_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)
PERCENT_ESCAPE_RE = re.compile(r"%[0-9A-Fa-f]{2}")


def _has_valid_percent_encoding(value: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] == "%":
            if index + 2 >= len(value) or not PERCENT_ESCAPE_RE.fullmatch(value[index:index + 3]):
                return False
            index += 3
            continue
        index += 1
    return True


def _canonical_path(value: str) -> Optional[str]:
    if (
        not isinstance(value, str)
        or not value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
        or not _has_valid_percent_encoding(value)
    ):
        return None
    if value.startswith("//"):
        return None

    canonical_parts = []
    for part in value.split("/"):
        if part in {".", ".."}:
            return None
        output = []
        index = 0
        while index < len(part):
            if part[index] != "%":
                output.append(part[index])
                index += 1
                continue
            byte = int(part[index + 1:index + 3], 16)
            if byte in {0x2F, 0x5C}:
                return None
            if byte in UNRESERVED_BYTES:
                output.append(chr(byte))
            else:
                output.append(f"%{byte:02X}")
            index += 3
        decoded = "".join(output)
        if decoded in {".", ".."}:
            return None
        canonical_parts.append(decoded)
    return "/".join(canonical_parts)


def _canonical_host(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value or any(ord(char) < 0x20 for char in value):
        return None
    try:
        return value.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None


def _safe_parse_url(target_url: Any) -> Optional[Any]:
    if not isinstance(target_url, str) or not target_url:
        return None
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in target_url) or "\\" in target_url:
        return None
    if not _has_valid_percent_encoding(target_url):
        return None
    try:
        parsed = urlparse(target_url)
        if parsed.username or parsed.password or parsed.fragment or parsed.hostname is None:
            return None
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https", "ws", "wss"}:
            return None
        port = parsed.port or (443 if scheme in {"https", "wss"} else 80)
        path = _canonical_path(parsed.path or "/")
        host = _canonical_host(parsed.hostname)
    except (TypeError, UnicodeError, ValueError):
        return None
    if path is None or host is None:
        return None
    return parsed, scheme, host, port, path


def query_policy_allows(scope: Dict[str, Any], parsed_query: str) -> bool:
    policy = scope.get("queryPolicy")
    if not isinstance(policy, dict):
        return False
    if not _has_valid_percent_encoding(parsed_query):
        return False
    if any(ord(char) < 0x20 or ord(char) == 0x7F or char == "\\" for char in parsed_query):
        return False
    try:
        pairs = parse_qsl(parsed_query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    if len({key for key, _ in pairs}) != len(pairs):
        return False
    mode = policy.get("mode")
    if mode == "deny":
        return not pairs
    if mode == "allow-all":
        return True
    if mode != "allow-listed":
        return False
    allowed_keys = set(policy.get("allowedKeys") or [])
    allowed_values = policy.get("allowedValues") or {}
    for key, value in pairs:
        if key not in allowed_keys:
            return False
        if key in allowed_values and value not in set(map(str, allowed_values[key])):
            return False
    return True


def scope_matches_route(scope: Dict[str, Any], target_url: str) -> bool:
    parsed_result = _safe_parse_url(target_url)
    if parsed_result is None or not isinstance(scope, dict):
        return False
    parsed, scheme, host, port, path = parsed_result
    scope_host = _canonical_host(scope.get("host"))
    try:
        scope_port = int(scope.get("port", -1))
    except (TypeError, ValueError):
        return False
    prefix = scope.get("routePrefix")
    if not isinstance(prefix, str):
        return False
    prefix = _canonical_path(prefix)
    if path is None or prefix is None:
        return False
    return (
        str(scope.get("scheme", "")).lower() == scheme
        and scope_host == host
        and scope_port == port
        and (path == prefix or path.startswith(prefix.rstrip("/") + "/"))
    )


def scope_allows(scopes: Iterable[Dict[str, Any]], target_url: str) -> bool:
    parsed_result = _safe_parse_url(target_url)
    if parsed_result is None:
        return False
    parsed = parsed_result[0]
    return any(
        scope_matches_route(scope, target_url) and query_policy_allows(scope, parsed.query)
        for scope in scopes
    )


def query_policy_covers(scope: Dict[str, Any], required_keys: set[str]) -> bool:
    policy = scope.get("queryPolicy")
    if not isinstance(policy, dict):
        return False
    mode = policy.get("mode")
    if mode == "allow-all":
        return True
    if mode == "deny":
        return not required_keys
    return mode == "allow-listed" and required_keys <= set(policy.get("allowedKeys") or [])


def route_scope_covers(
    scopes: Iterable[Dict[str, Any]], target_url: str, required_query_keys: set[str]
) -> bool:
    return any(
        scope_matches_route(scope, target_url)
        and query_policy_covers(scope, required_query_keys)
        for scope in scopes
    )


def buffer_response_with_cap(response: Any, byte_cap: int) -> Any:
    """Read a streamed response only up to the immutable response-byte cap."""
    if byte_cap < 1:
        raise ValueError("response byte cap must be positive")
    content_length = response.headers.get("content-length") if hasattr(response, "headers") else None
    if content_length:
        try:
            if int(content_length) > byte_cap:
                response.close()
                raise ValueError("GT4 response exceeds the approved byte cap")
        except ValueError:
            if str(content_length).isdigit():
                raise
    payload = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=min(65536, byte_cap)):
            if not chunk:
                continue
            if len(payload) + len(chunk) > byte_cap:
                raise ValueError("GT4 response exceeds the approved byte cap")
            payload.extend(chunk)
    except Exception:
        response.close()
        raise
    response._content = bytes(payload)
    response._content_consumed = True
    return response


def validate_ledger_path(work_order: Dict[str, Any]) -> Path:
    authorization = work_order.get("authorization") or {}
    budget = authorization.get("requestBudget") or {}
    ledger_id = budget.get("budgetLedgerId")
    ledger_value = budget.get("ledgerPath")
    work_order_id = work_order.get("workOrderId")
    if not isinstance(work_order_id, str) or not work_order_id:
        raise ValueError("workOrderId is required for a persistent budget ledger")
    expected_ledger_id = hashlib.sha256(work_order_id.encode("utf-8")).hexdigest()
    if not isinstance(ledger_id, str) or ledger_id != expected_ledger_id or not LEDGER_ID_RE.fullmatch(ledger_id):
        raise ValueError("requestBudget.budgetLedgerId must equal sha256(workOrderId)")
    expected_ledger_path = f"js_reverse_cache/private/gt4-ledgers/{ledger_id}/ledger.sqlite3"
    if ledger_value != expected_ledger_path:
        raise ValueError("requestBudget.ledgerPath must use the canonical ledger path for its work order")
    project = work_order.get("project") or {}
    project_root = Path(str(project.get("projectRoot") or ""))
    if not project_root.is_absolute():
        raise ValueError("project.projectRoot must be absolute")
    project_root = ensure_plain_directory(project_root, create=False)
    ledger_path = _project_path(project_root, ledger_value, "requestBudget.ledgerPath")
    if project.get("writeMode") != "modify-allowlisted":
        raise ValueError("persistent budget ledger requires project.writeMode=modify-allowlisted")
    ledger_allowed = any(
        isinstance(raw_path, str)
        and raw_path.endswith("/**")
        and _allowed_contains(project_root, [raw_path], ledger_path)
        for raw_path in project.get("allowedPaths") or []
    )
    if not ledger_allowed:
        raise ValueError("requestBudget.ledgerPath must stay under an allowed ledger subtree")
    return ledger_path


def _scope_fingerprint(scopes: Any) -> str:
    payload = json.dumps(scopes, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BudgetLedger:
    """Append-only budget ledger with leases for real GT4 request starts."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        ledger_id: str,
        total: int,
        initial_remaining: int,
        min_delay_ms: int,
        concurrency: int,
    ) -> None:
        self._connection = connection
        self.ledger_id = ledger_id
        self.total = total
        self.initial_remaining = initial_remaining
        self.min_delay_ms = min_delay_ms
        self.concurrency = concurrency

    @classmethod
    def open(cls, work_order: Dict[str, Any]) -> "BudgetLedger":
        authorization = work_order.get("authorization") or {}
        budget = authorization.get("requestBudget") or {}
        try:
            total = int(budget["total"])
            initial_remaining = int(budget["remaining"])
            min_delay_ms = int(budget["minDelayMs"])
            concurrency = int(budget["concurrency"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "requestBudget total, remaining, minDelayMs, and concurrency must be integers"
            ) from error
        if total < 1 or not 0 < initial_remaining <= total:
            raise ValueError("GT4 live work order needs 0 < remaining <= total")
        if min_delay_ms < 0:
            raise ValueError("requestBudget.minDelayMs must not be negative")
        if concurrency < 1:
            raise ValueError("requestBudget.concurrency must be positive")
        ledger_path = validate_ledger_path(work_order)
        existed = os.path.lexists(ledger_path)
        if existed:
            ensure_plain_file(ledger_path)
        else:
            ensure_plain_directory(ledger_path.parent, create=True)

        connection = sqlite3.connect(str(ledger_path), timeout=30, isolation_level=None)
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        ledger = cls(
            connection,
            str(budget["budgetLedgerId"]),
            total,
            initial_remaining,
            min_delay_ms,
            concurrency,
        )
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reservations ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "kind TEXT NOT NULL, target_sha256 TEXT NOT NULL, state TEXT NOT NULL, "
                "reserved_ms INTEGER NOT NULL, started_ms INTEGER, completed_ms INTEGER, "
                "lease_expires_ms INTEGER)"
            )
            connection.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            rows = dict(connection.execute("SELECT key, value FROM meta"))
            expected = {
                "budgetLedgerId": ledger.ledger_id,
                "workOrderId": str(work_order.get("workOrderId") or ""),
                "total": str(total),
                "initialRemaining": str(initial_remaining),
                "minDelayMs": str(min_delay_ms),
                "concurrency": str(concurrency),
                "scopeSha256": _scope_fingerprint(authorization.get("allowedHostsAndRoutes") or []),
            }
            if rows:
                if rows != expected:
                    raise BudgetError("budget ledger does not match this immutable work order")
            elif existed:
                raise BudgetError("existing budget ledger is missing its immutable header")
            else:
                connection.executemany("INSERT INTO meta(key, value) VALUES (?, ?)", expected.items())
                connection.execute("INSERT INTO state(key, value) VALUES ('maxConcurrencyObserved', '0')")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            connection.close()
            raise
        return ledger

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "BudgetLedger":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def _snapshot_locked(self, now_ms: int) -> Dict[str, Any]:
        rows = dict(self._connection.execute("SELECT kind, COUNT(*) FROM reservations GROUP BY kind"))
        by_kind = {kind: int(rows.get(kind, 0)) for kind in BUDGET_KINDS}
        consumed = sum(by_kind.values())
        active = int(
            self._connection.execute(
                "SELECT COUNT(*) FROM reservations WHERE state = 'active' AND lease_expires_ms > ?",
                (now_ms,),
            ).fetchone()[0]
        )
        max_active_row = self._connection.execute(
            "SELECT value FROM state WHERE key = 'maxConcurrencyObserved'"
        ).fetchone()
        max_active = int(max_active_row[0]) if max_active_row else 0
        return {
            "budgetLedgerId": self.ledger_id,
            "total": self.total,
            "priorRemaining": self.initial_remaining,
            "consumed": consumed,
            "remaining": self.initial_remaining - consumed,
            "byKind": by_kind,
            "minDelayMsApplied": self.min_delay_ms,
            "activeRequests": active,
            "maxConcurrencyObserved": max_active,
        }

    def snapshot(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        return self._snapshot_locked(now_ms)

    def _expire_leases_locked(self, now_ms: int) -> None:
        self._connection.execute(
            "UPDATE reservations SET state = 'abandoned', completed_ms = ? "
            "WHERE state = 'active' AND lease_expires_ms <= ?",
            (now_ms, now_ms),
        )

    def reserve(self, kind: str, target_url: str) -> Dict[str, Any]:
        if kind not in BUDGET_KINDS:
            raise ValueError(f"unknown budget kind: {kind}")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            now_ms = int(time.time() * 1000)
            self._expire_leases_locked(now_ms)
            current = self._snapshot_locked(now_ms)
            if current["remaining"] <= 0:
                raise BudgetError("live verifier request budget exhausted")
            target_digest = hashlib.sha256(target_url.encode("utf-8")).hexdigest()
            cursor = self._connection.execute(
                "INSERT INTO reservations(kind, target_sha256, state, reserved_ms) VALUES (?, ?, 'reserved', ?)",
                (kind, target_digest, now_ms),
            )
            self._connection.execute("COMMIT")
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        if cursor.lastrowid is None:
            raise BudgetError("GT4 budget ledger did not return a reservation id")
        snapshot = self.snapshot()
        snapshot["reservationId"] = int(cursor.lastrowid)
        return snapshot

    def begin_request(
        self,
        kind: str,
        target_url: str,
        request_timeout_ms: int,
        acquisition_timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        if request_timeout_ms < 1 or acquisition_timeout_ms < 1:
            raise ValueError("request and acquisition timeouts must be positive")
        reservation = self.reserve(kind, target_url)
        reservation_id = int(reservation["reservationId"])
        deadline_ms = int(time.time() * 1000) + acquisition_timeout_ms
        while True:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                now_ms = int(time.time() * 1000)
                self._expire_leases_locked(now_ms)
                active = int(
                    self._connection.execute(
                        "SELECT COUNT(*) FROM reservations WHERE state = 'active' AND lease_expires_ms > ?",
                        (now_ms,),
                    ).fetchone()[0]
                )
                latest_started = self._connection.execute(
                    "SELECT MAX(started_ms) FROM reservations WHERE started_ms IS NOT NULL"
                ).fetchone()[0]
                not_before_ms = int(latest_started or 0) + self.min_delay_ms
                wait_ms = max(0, not_before_ms - now_ms)
                if active < self.concurrency and wait_ms == 0:
                    lease_expires_ms = now_ms + request_timeout_ms + 1000
                    self._connection.execute(
                        "UPDATE reservations SET state = 'active', started_ms = ?, lease_expires_ms = ? "
                        "WHERE sequence = ? AND state = 'reserved'",
                        (now_ms, lease_expires_ms, reservation_id),
                    )
                    max_active = active + 1
                    self._connection.execute(
                        "INSERT INTO state(key, value) VALUES ('maxConcurrencyObserved', ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = "
                        "MAX(CAST(value AS INTEGER), CAST(excluded.value AS INTEGER))",
                        (str(max_active),),
                    )
                    self._connection.execute("COMMIT")
                    snapshot = self.snapshot()
                    snapshot["reservationId"] = reservation_id
                    return snapshot
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise
            now_ms = int(time.time() * 1000)
            if now_ms >= deadline_ms:
                raise BudgetError("GT4 request reservation could not acquire concurrency/delay lease")
            time.sleep(min(max(wait_ms, 1), 50) / 1000)

    def finish_request(self, reservation_id: int) -> None:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute(
                "UPDATE reservations SET state = 'complete', completed_ms = ?, lease_expires_ms = NULL "
                "WHERE sequence = ? AND state = 'active'",
                (int(time.time() * 1000), reservation_id),
            )
            self._connection.execute("COMMIT")
        except Exception:
            self._connection.execute("ROLLBACK")
            raise


def require_unexpired_approval_deadline(value: Any) -> None:
    if not isinstance(value, str) or not value:
        raise SandboxError("target-code approval deadline is required")
    try:
        deadline = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SandboxError("target-code approval deadline must be ISO-8601") from error
    if deadline.tzinfo is None or deadline <= datetime.now(timezone.utc):
        raise SandboxError("target-code approval deadline is expired or lacks a timezone")


def require_sandbox_adapter(execution_policy: Dict[str, Any]) -> None:
    sandbox = execution_policy.get("sandbox") or {}
    if sandbox.get("backend") != "capability-denied-external":
        raise SandboxError("target JS requires a capability-denied external sandbox")
    raise SandboxError(
        "no reviewed capability-denied sandbox adapter is bundled; "
        "GT4 target-JS replay is disabled, so use gt4_pure_replay.py"
    )
