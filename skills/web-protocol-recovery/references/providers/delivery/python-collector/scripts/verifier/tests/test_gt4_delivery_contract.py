"""Offline regression tests owned by the GT4 delivery template."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import tempfile
import time
import unittest
from pathlib import Path


VERIFIER_DIR = Path(__file__).resolve().parents[1]
SKILL_ROOT = VERIFIER_DIR.parents[5]
RUNTIME_PATH = VERIFIER_DIR / "gt4_runtime.py"
SPEC = importlib.util.spec_from_file_location("gt4_runtime", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
gt4_runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gt4_runtime)


def work_order(root: Path) -> dict:
    work_order_id = "gt4-contract-test"
    ledger_id = hashlib.sha256(work_order_id.encode("utf-8")).hexdigest()
    return {
        "workOrderId": work_order_id,
        "authorization": {
            "allowedHostsAndRoutes": [
                {
                    "scheme": "https",
                    "host": "gcaptcha4.geetest.com",
                    "port": 443,
                    "routePrefix": "/load",
                    "queryPolicy": {
                        "mode": "allow-listed",
                        "allowedKeys": ["callback", "captcha_id", "challenge", "client_type", "risk_type", "pt", "lang"],
                    },
                },
                {
                    "scheme": "https",
                    "host": "gcaptcha4.geetest.com",
                    "port": 443,
                    "routePrefix": "/verify",
                    "queryPolicy": {
                        "mode": "allow-listed",
                        "allowedKeys": ["callback", "captcha_id", "client_type", "lot_number", "risk_type", "payload", "process_token", "payload_protocol", "pt", "w", "td", "td_sign"],
                    },
                },
                {
                    "scheme": "https",
                    "host": "static.geetest.com",
                    "port": 443,
                    "routePrefix": "/",
                    "queryPolicy": {"mode": "deny"},
                },
            ],
            "requestBudget": {
                "total": 5,
                "remaining": 5,
                "minDelayMs": 50,
                "concurrency": 1,
                "budgetLedgerId": ledger_id,
                "ledgerPath": f"js_reverse_cache/private/gt4-ledgers/{ledger_id}/ledger.sqlite3",
            },
        },
        "project": {
            "projectRoot": str(root),
            "writeMode": "modify-allowlisted",
            "allowedPaths": [
                "js_reverse_cache/source/geetest_gt4/**",
                f"js_reverse_cache/private/gt4-ledgers/{ledger_id}/**",
            ],
        },
    }


class Gt4BudgetLedgerTests(unittest.TestCase):
    def test_reopen_does_not_reset_immutable_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            order = work_order(root)
            ledger = gt4_runtime.BudgetLedger.open(order)
            try:
                for _ in range(5):
                    ledger.reserve("request", "https://gcaptcha4.geetest.com/load")
                self.assertEqual(ledger.snapshot()["remaining"], 0)
            finally:
                ledger.close()
            reopened = gt4_runtime.BudgetLedger.open(order)
            try:
                self.assertEqual(reopened.snapshot()["remaining"], 0)
                with self.assertRaises(gt4_runtime.BudgetError):
                    reopened.reserve("request", "https://gcaptcha4.geetest.com/load")
            finally:
                reopened.close()

    def test_reservation_is_not_refunded_and_schedules_minimum_delay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            order = work_order(root)
            ledger = gt4_runtime.BudgetLedger.open(order)
            try:
                first = ledger.begin_request(
                    "request", "https://gcaptcha4.geetest.com/load", 1000
                )
                ledger.finish_request(first["reservationId"])
                started = time.monotonic()
                second = ledger.begin_request(
                    "request", "https://gcaptcha4.geetest.com/static", 1000
                )
                self.assertGreaterEqual(time.monotonic() - started, 0.04)
                ledger.finish_request(second["reservationId"])
            finally:
                ledger.close()
            reopened = gt4_runtime.BudgetLedger.open(order)
            try:
                self.assertEqual(reopened.snapshot()["consumed"], 2)
                self.assertEqual(reopened.snapshot()["remaining"], 3)
            finally:
                reopened.close()

    def test_active_lease_enforces_declared_concurrency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            ledger = gt4_runtime.BudgetLedger.open(work_order(root))
            try:
                active = ledger.begin_request(
                    "request", "https://gcaptcha4.geetest.com/load", 1000
                )
                with self.assertRaises(gt4_runtime.BudgetError):
                    ledger.begin_request(
                        "request",
                        "https://gcaptcha4.geetest.com/static",
                        1000,
                        acquisition_timeout_ms=1,
                    )
                ledger.finish_request(active["reservationId"])
                self.assertEqual(ledger.snapshot()["maxConcurrencyObserved"], 1)
            finally:
                ledger.close()

    def test_ledger_rejects_drifted_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            order = work_order(root)
            ledger = gt4_runtime.BudgetLedger.open(order)
            ledger.close()
            changed = copy.deepcopy(order)
            changed["authorization"]["requestBudget"]["total"] = 6
            with self.assertRaises(gt4_runtime.BudgetError):
                gt4_runtime.BudgetLedger.open(changed)


class Gt4FilesystemAndScopeTests(unittest.TestCase):
    def test_cache_lot_and_artifacts_are_create_only_and_contained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            cache_root = root / "js_reverse_cache" / "source" / "geetest_gt4"
            gt4_runtime.ensure_plain_directory(cache_root, create=True)
            lot = gt4_runtime.create_exclusive_directory(
                gt4_runtime.safe_lot_cache(cache_root, "lot123")
            )
            gt4_runtime.write_new_text(lot / "load.json", "{}\n")
            with self.assertRaises(FileExistsError):
                gt4_runtime.create_exclusive_directory(gt4_runtime.safe_lot_cache(cache_root, "lot123"))
            with self.assertRaises(FileExistsError):
                gt4_runtime.write_new_text(lot / "load.json", "{}\n")
            for malicious in (
                "..", "C:/outside", "C:\\outside", "/outside", "CON", "NUL", "COM1", "lot."
            ):
                with self.subTest(lot=malicious):
                    with self.assertRaises(ValueError):
                        gt4_runtime.safe_lot_cache(cache_root, malicious)

    def test_cache_and_ledger_must_use_allowlisted_subtrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            order = work_order(root)
            cache = root / "js_reverse_cache" / "source" / "geetest_gt4"
            self.assertEqual(gt4_runtime.validate_cache_root(order["project"], cache), cache)
            self.assertTrue(str(gt4_runtime.validate_ledger_path(order)).endswith("ledger.sqlite3"))
            bad = copy.deepcopy(order)
            bad["project"]["writeMode"] = "create-only"
            with self.assertRaises(ValueError):
                gt4_runtime.validate_ledger_path(bad)
            exact_ledger = copy.deepcopy(order)
            exact_ledger["project"]["allowedPaths"][1] = exact_ledger["authorization"]["requestBudget"]["ledgerPath"]
            with self.assertRaises(ValueError):
                gt4_runtime.validate_ledger_path(exact_ledger)
            changed_path = copy.deepcopy(order)
            changed_path["authorization"]["requestBudget"]["ledgerPath"] = "js_reverse_cache/private/other.sqlite3"
            with self.assertRaises(ValueError):
                gt4_runtime.validate_ledger_path(changed_path)

    def test_encoded_or_dot_segment_route_is_not_allowlisted(self) -> None:
        scopes = work_order(Path.cwd())["authorization"]["allowedHostsAndRoutes"]
        scopes[0]["routePrefix"] = "/api"
        self.assertFalse(
            gt4_runtime.scope_allows(
                scopes, "https://gcaptcha4.geetest.com/api/%2e%2e/private"
            )
        )
        self.assertFalse(
            gt4_runtime.scope_allows(scopes, "https://gcaptcha4.geetest.com/api/../private")
        )
        self.assertTrue(gt4_runtime.scope_allows(scopes, "https://gcaptcha4.geetest.com/api/load"))

    def test_invalid_url_fails_closed_without_raising(self) -> None:
        scopes = work_order(Path.cwd())["authorization"]["allowedHostsAndRoutes"]
        for target in ("https://[bad/api", "", None, "https://gcaptcha4.geetest.com/%2Fprivate"):
            with self.subTest(target=target):
                self.assertFalse(gt4_runtime.scope_allows(scopes, target))

    def test_websocket_scope_supports_handshake_only(self) -> None:
        scope = {
            "scheme": "wss",
            "host": "stream.example.test",
            "port": 443,
            "routePrefix": "/socket",
            "queryPolicy": {"mode": "deny"},
        }
        self.assertTrue(gt4_runtime.scope_allows([scope], "wss://stream.example.test/socket"))
        self.assertFalse(gt4_runtime.scope_allows([scope], "wss://stream.example.test/private"))
        self.assertFalse(gt4_runtime.scope_allows([scope], "https://stream.example.test/socket"))

    def test_generic_root_scope_matching_is_not_gt4_validation(self) -> None:
        scope = {
            "scheme": "https",
            "host": "gcaptcha4.geetest.com",
            "port": 443,
            "routePrefix": "/",
            "queryPolicy": {"mode": "allow-all"},
        }
        self.assertTrue(gt4_runtime.scope_allows([scope], "https://gcaptcha4.geetest.com/load"))
        self.assertTrue(gt4_runtime.scope_allows([scope], "https://gcaptcha4.geetest.com/admin/export?token=x"))

    def test_response_body_cap_stops_buffering_before_overflow(self) -> None:
        class FakeResponse:
            def __init__(self, chunks, content_length=None):
                self.headers = {} if content_length is None else {"content-length": str(content_length)}
                self._chunks = chunks
                self.closed = False

            def iter_content(self, chunk_size):
                yield from self._chunks

            def close(self):
                self.closed = True

        response = FakeResponse([b"abc", b"def"])
        buffered = gt4_runtime.buffer_response_with_cap(response, 6)
        self.assertEqual(buffered._content, b"abcdef")
        oversized = FakeResponse([b"abcdef"])
        with self.assertRaisesRegex(ValueError, "byte cap"):
            gt4_runtime.buffer_response_with_cap(oversized, 5)
        self.assertTrue(oversized.closed)


class Gt4ExecutionBoundaryTests(unittest.TestCase):
    def test_gt4_templates_bind_slider_sidecar_and_semantic_success(self) -> None:
        node_template = (VERIFIER_DIR / "gt4_replay.py").read_text(encoding="utf-8")
        pure_template = (VERIFIER_DIR / "gt4_pure_replay.py").read_text(encoding="utf-8")
        for text in (node_template, pure_template):
            self.assertIn('"td": td', text)
            self.assertIn('"td_sign": td_sign', text)
            self.assertIn('verify_json.get("data", {}).get("fail_count") == 0', text)
            self.assertIn('"credentialHandoff"', text)

    def test_unverified_sandbox_declaration_is_rejected(self) -> None:
        with self.assertRaises(gt4_runtime.SandboxError):
            gt4_runtime.require_sandbox_adapter(
                {"sandbox": {"backend": "capability-denied-external"}}
            )

    def test_templates_have_no_direct_node_or_overwrite_path(self) -> None:
        node_template = (VERIFIER_DIR / "gt4_replay.py").read_text(encoding="utf-8")
        pure_template = (VERIFIER_DIR / "gt4_pure_replay.py").read_text(encoding="utf-8")
        for text in (node_template, pure_template):
            self.assertIn("BudgetLedger", text)
            self.assertIn("create_exclusive_directory", text)
            self.assertIn("rawSecretHandling", text)
            self.assertIn("session.prepare_request", text)
            self.assertIn("session.send", text)
            self.assertIn("buffer_response_with_cap", text)
            self.assertNotIn("session.get(", text)
            self.assertNotIn("exist_ok=True", text)
        self.assertIn("require_sandbox_adapter", node_template)
        self.assertNotIn("run_sandboxed_json", node_template)
        self.assertNotIn("--helper", node_template)

    def test_helper_is_an_explicit_fail_closed_stub(self) -> None:
        helper = (
            SKILL_ROOT
            / "references"
            / "providers"
            / "implementation"
            / "python-node"
            / "scripts"
            / "gt4_bundle_helper.js"
        ).read_text(encoding="utf-8")
        self.assertIn("target-JS bundle execution is disabled", helper)
        self.assertNotIn("require('fs')", helper)
        self.assertNotIn("require('vm')", helper)
        self.assertNotIn("vm.runInContext", helper)


if __name__ == "__main__":
    unittest.main(verbosity=2)
