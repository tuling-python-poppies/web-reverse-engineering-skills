import base64
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


GATES_DIR = Path(__file__).resolve().parents[1] / "gates"
SPEC = importlib.util.spec_from_file_location("preflight", GATES_DIR / "preflight.py")
assert SPEC is not None
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(preflight)
VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_case_hashes", GATES_DIR / "verify_case_hashes.py"
)
assert VERIFY_SPEC is not None
verify_case_hashes = importlib.util.module_from_spec(VERIFY_SPEC)
assert VERIFY_SPEC.loader is not None
VERIFY_SPEC.loader.exec_module(verify_case_hashes)


class EntryDisciplineScanTests(unittest.TestCase):
    def scan_ast(self, source: str) -> list[str]:
        path = preflight.SKILL_ROOT / "references" / "cases" / "iv8" / "jd-h5st" / "entry.py"
        return preflight.scan_entry_ast(path, source)

    def assert_warns(self, source: str, needle: str) -> None:
        warnings = self.scan_ast(source)
        self.assertTrue(
            any(needle in warning for warning in warnings),
            f"missing {needle!r} in {warnings!r}",
        )

    def test_requests_alias_call_is_import_time_side_effect(self) -> None:
        self.assert_warns(
            'import requests as rq\nresponse = rq.get("https://example.test")\n',
            "module-level assign with side-effect call",
        )

    def test_from_requests_get_call_is_import_time_side_effect(self) -> None:
        self.assert_warns(
            'from requests import get\nresponse = get("https://example.test")\n',
            "module-level assign with side-effect call",
        )

    def test_from_requests_session_binding_is_import_time_side_effect(self) -> None:
        self.assert_warns(
            'from requests import Session\nsession = Session()\n',
            "module-level assign with side-effect call",
        )

    def test_unguarded_local_function_call_is_import_time_side_effect(self) -> None:
        self.assert_warns(
            'def fetch():\n    import requests\n    return requests.get("https://example.test")\n\nfetch()\n',
            "module-level call into side-effect function",
        )

    def test_main_guard_allows_live_runtime_path(self) -> None:
        warnings = self.scan_ast(
            'def main():\n    import requests\n    return requests.get("https://example.test")\n\n'
            'if __name__ == "__main__":\n    main()\n'
        )
        self.assertEqual([], warnings)

    def test_curl_cffi_requests_alias_is_import_time_side_effect(self) -> None:
        self.assert_warns(
            'from curl_cffi import requests as crequests\nresponse = crequests.get("https://example.test")\n',
            "module-level assign with side-effect call",
        )

    def test_path_read_text_is_import_time_side_effect(self) -> None:
        self.assert_warns(
            'from pathlib import Path\nsource = Path("asset.js").read_text(encoding="utf-8")\n',
            "module-level assign with side-effect call",
        )


class PreflightSelfTestGateTests(unittest.TestCase):
    def test_missing_self_test_file_fails_closed(self) -> None:
        missing = preflight.SKILL_ROOT / "scripts" / "tests" / "test_preflight.py"
        with mock.patch.object(Path, "is_file", return_value=False):
            ok, out = preflight.check_preflight_unit_tests()
        self.assertFalse(ok)
        self.assertIn("MISSING", out)
        self.assertTrue(missing.name.endswith("test_preflight.py"))

    def test_skip_tests_still_runs_self_tests(self) -> None:
        with (
            mock.patch.object(preflight, "check_hashes", return_value=(True, "hash ok")),
            mock.patch.object(
                preflight,
                "check_case_registry_projection",
                return_value=(True, "registry ok"),
            ),
            mock.patch.object(
                preflight,
                "check_architecture_contract",
                return_value=(True, "architecture ok"),
            ),
            mock.patch.object(
                preflight,
                "check_route_regression_evals",
                return_value=(True, "evals ok"),
            ),
            mock.patch.object(preflight, "scan_entries", return_value=[]),
            mock.patch.object(
                preflight,
                "check_preflight_unit_tests",
                return_value=(True, "self tests ok"),
            ) as self_tests,
            mock.patch.object(
                preflight,
                "check_diagnostic_self_tests",
                return_value=(True, "diagnostic tests ok"),
            ) as diagnostic_tests,
            mock.patch.object(
                preflight,
                "check_provider_guard_contracts",
                return_value=(True, "guards ok"),
            ),
            mock.patch.object(
                preflight,
                "check_commit_body_policy",
                return_value=(True, "commit policy ok"),
            ),
            mock.patch.object(preflight, "discover_test_cases") as discover,
            mock.patch.object(preflight, "check_case_tests") as case_tests,
            redirect_stdout(io.StringIO()),
        ):
            code = preflight.main(["--skip-tests"])
        self.assertEqual(0, code)
        self_tests.assert_called_once()
        diagnostic_tests.assert_called_once()
        discover.assert_not_called()
        case_tests.assert_not_called()


class DiagnosticSelfTestGateTests(unittest.TestCase):
    def test_missing_diagnostic_script_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ok, out = preflight.check_diagnostic_self_tests(
                ("scripts/missing.py",),
                Path(tmp),
            )
        self.assertFalse(ok)
        self.assertEqual("MISSING scripts/missing.py", out)

    def test_diagnostic_script_runs_self_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "tool.py").write_text("pass\n", encoding="utf-8")
            with mock.patch.object(
                preflight,
                "run",
                return_value=(0, "tool_self_test=PASS\n"),
            ) as runner:
                ok, out = preflight.check_diagnostic_self_tests(
                    ("scripts/tool.py",),
                    root,
                )
        self.assertTrue(ok, out)
        command = runner.call_args.args[0]
        self.assertEqual("--self-test", command[-1])


class ProviderGuardContractTests(unittest.TestCase):
    def test_current_provider_guard_contracts_pass(self) -> None:
        ok, out = preflight.check_provider_guard_contracts()
        self.assertTrue(ok, out)

    def test_missing_provider_guard_token_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "demo.js"
            path.write_text("console.log('unguarded')\n", encoding="utf-8")
            findings = preflight.provider_guard_contract_findings(
                root,
                (("demo.js", ("WPR_APPROVED_TEMPLATE_LIVE_EGRESS",), "demo guard"),),
                gt4_scripts=(),
            )
        self.assertEqual(
            ["demo guard: demo.js missing token(s): WPR_APPROVED_TEMPLATE_LIVE_EGRESS"],
            findings,
        )

    def test_bare_session_get_outside_live_get_is_detected(self) -> None:
        text = (
            "def live_get(session, url, **kwargs):\n"
            "    return session.get(url, **kwargs)\n"
            "\n"
            "def main():\n"
            "    session.get('https://example.com')\n"
        )
        self.assertEqual([5], preflight.bare_session_get_outside_live_get(text))

    def test_session_get_inside_live_get_is_allowed(self) -> None:
        text = (
            "def live_get(session, url, **kwargs):\n"
            "    require_live_verify_approval()\n"
            "    return session.get(url, **kwargs)\n"
            "\n"
            "def main():\n"
            "    return live_get(session, 'https://example.com')\n"
        )
        self.assertEqual([], preflight.bare_session_get_outside_live_get(text))


class AliyunV2ReferenceContractTests(unittest.TestCase):
    REFERENCE = (
        preflight.SKILL_ROOT
        / "references"
        / "providers"
        / "protocol-recovery"
        / "verifier"
        / "references"
        / "aliyun-captcha-v2-workflow.md"
    )

    def test_generation_signals_precede_shared_sidecar_evidence(self) -> None:
        text = self.REFERENCE.read_text(encoding="utf-8")
        for token in (
            "至少看到一个 V2 代际信号时才使用本参考",
            "只能作为阿里云 verifier/sidecar 佐证，不能单独区分 V2/V3",
            "不要按表格顺序选 V2，也不要同时预读 V2/V3",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_active_guidance_has_no_local_project_schema_assumptions(self) -> None:
        text = self.REFERENCE.read_text(encoding="utf-8")
        for obsolete in (
            "看到以下任一组信号时使用本参考",
            "本目录 ≥3 个 session suffix",
            "本目录同轮 capture",
            "profile.feilinVersion",
            "纯协议 runner 验收 T001",
            "写进 skill，直接用",
            "写入 skill，禁止每轮重解",
            "单 profile 的纯协议 runner",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, text)

    def test_rpc_credentials_are_current_target_inputs(self) -> None:
        text = self.REFERENCE.read_text(encoding="utf-8")
        for token in (
            "RPC AK/签名 secret 是当前目标输入，不是协议族固定常量",
            "不在 skill、case 或日志中持久化",
            "MAIN_AK     = <CURRENT_TARGET_MAIN_AK>",
            "MAIN_SECRET = <CURRENT_TARGET_MAIN_SIGNING_SECRET>",
            "DEVICE_AK     = <CURRENT_TARGET_DEVICE_AK>",
            "DEVICE_SECRET = <CURRENT_TARGET_DEVICE_SIGNING_SECRET>",
            "AccessKeyId = <CURRENT_TARGET_DEVICE_AK>",
            "secret      = <CURRENT_TARGET_DEVICE_SIGNING_SECRET>",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)
        self.assertNotRegex(
            text,
            r"(?im)^\s*(?:(?:MAIN|DEVICE)_(?:AK|SECRET)|AccessKeyId|secret)"
            r"\s*=\s*(?!<CURRENT_TARGET_)[^\s#]{8,}",
        )


class AliyunV3ReferenceContractTests(unittest.TestCase):
    REFERENCE = (
        preflight.SKILL_ROOT
        / "references"
        / "providers"
        / "protocol-recovery"
        / "verifier"
        / "references"
        / "aliyun-captcha-v3-workflow.md"
    )

    @staticmethod
    def build_field21(suffix: str, source_key: str, xor_mask: bytes) -> str:
        if len(suffix) != 8 or len(source_key) != 8 or len(xor_mask) != 8:
            raise ValueError("field21 inputs must all be 8 bytes or characters")
        mixed = bytes(
            32 + ((ord(source) - 32 + ord(local) - 32) % 95)
            for source, local in zip(source_key, suffix)
        )
        return base64.b64encode(
            bytes(value ^ mask for value, mask in zip(mixed, xor_mask))
        ).decode("ascii")

    def test_documented_field21_vectors(self) -> None:
        vectors = (
            ("983c7551", "68fded68", bytes.fromhex("3331663739646463"), "fGEff0UdLyo="),
            ("e7f61587", "cccccccc", bytes(8), "SXpKeXR4e3o="),
            ("2f894218", "cccccccc", bytes(8), "dUp7fHd1dHs="),
            ("58c88084", "========", bytes.fromhex("3037326538323930"), "YmITMG1/bGE="),
            ("554f0616", "========", bytes.fromhex("3037326538323930"), "YmVjQXVhd2M="),
        )
        for suffix, source_key, xor_mask, expected in vectors:
            with self.subTest(suffix=suffix, source_key=source_key):
                self.assertEqual(
                    expected,
                    self.build_field21(suffix, source_key, xor_mask),
                )

    def test_reference_binds_mask_encodings_and_vectors(self) -> None:
        text = self.REFERENCE.read_text(encoding="utf-8")
        for token in (
            "xorMaskHex  = 3331663739646463",
            "xorMaskHex  = 0000000000000000",
            "xorMaskHex  = 3037326538323930",
            "983c7551 -> fGEff0UdLyo=",
            "e7f61587 -> SXpKeXR4e3o=",
            "58c88084 -> YmITMG1/bGE=",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_reference_documents_log2_envelope_layers(self) -> None:
        text = self.REFERENCE.read_text(encoding="utf-8")
        for token in (
            'event_data = "#".join(outer_fields[-2:])',
            'event_type, record_b64 = event_data.split("#", 1)',
            'assert event_type == "501"',
            "record_fields = Base64Decode(record_b64).decode().split(\"#\")",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_historical_sample_uses_target_state_language(self) -> None:
        text = self.REFERENCE.read_text(encoding="utf-8")
        self.assertIn("历史目标状态仍记录 `feilin107...`", text)
        self.assertNotIn("本地 profile 仍是 `feilin107...`", text)


class CaseArchiveContractTests(unittest.TestCase):
    def test_active_python_and_javascript_archive_references_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.py").write_text(
                'ARCHIVE = "case-live-reference-archive"\n', encoding="utf-8"
            )
            (root / "helper.js").write_text(
                'const archive = "case-live-reference-archive";\n', encoding="utf-8"
            )
            findings = verify_case_hashes.active_archive_load_findings(root)
        self.assertEqual(2, len(findings))
        self.assertTrue(any(item.startswith("entry.py:1:") for item in findings))
        self.assertTrue(any(item.startswith("helper.js:1:") for item in findings))

    def test_sensitive_dictionary_value_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.py").write_text(
                'CONFIG = {"access_token": "not-empty"}\n', encoding="utf-8"
            )
            findings = verify_case_hashes.sensitive_literal_findings(root)
        self.assertEqual(
            [("references/case-live-reference-archive/entry.py", "dict-value:access_token")],
            findings,
        )

    def test_all_fresh_implementations_require_hash_binding(self) -> None:
        historical = {
            "caseKind": "implementation",
            "verificationClass": "historical-user-attested",
        }
        evidence = {
            "caseKind": "evidence",
            "verificationClass": "freshly-verified",
        }
        implementation = {
            "caseKind": "implementation",
            "verificationClass": "freshly-verified",
        }
        self.assertFalse(verify_case_hashes.requires_current_proof_binding(historical))
        self.assertFalse(verify_case_hashes.requires_current_proof_binding(evidence))
        self.assertTrue(verify_case_hashes.requires_current_proof_binding(implementation))

    def test_evidence_process_active_implementation_claims_fail(self) -> None:
        text = (
            "Read this case's entry.py.\n"
            "verificationClass freshly-verified\n"
            "CASE_LIVE=1 python helper.py\n"
        )
        self.assertEqual(
            [
                "references active entry.py",
                "claims freshly-verified status",
                "contains active live command",
            ],
            verify_case_hashes.evidence_process_claim_findings(text),
        )
        self.assertEqual(
            [],
            verify_case_hashes.evidence_process_claim_findings(
                "Historical process evidence only; archived code is study-only."
            ),
        )

class CommitBodyPolicyTests(unittest.TestCase):
    def test_subject_only_message_has_no_body(self) -> None:
        self.assertFalse(preflight.has_commit_body("subject only\n"))
        self.assertTrue(preflight.has_commit_body("subject\n\nwhy: changed threshold\n"))

    def test_hash_bound_case_path_requires_body(self) -> None:
        self.assertTrue(
            preflight.is_hash_bound_case_path(
                "skills/web-protocol-recovery/references/cases/iv8/demo/case.json",
                "skills/web-protocol-recovery",
            )
        )

    def test_tool_residue_case_path_is_ignored(self) -> None:
        self.assertFalse(
            preflight.is_hash_bound_case_path(
                "skills/web-protocol-recovery/references/cases/iv8/demo/__pycache__/entry.pyc",
                "skills/web-protocol-recovery",
            )
        )

    def test_registry_selection_diff_requires_body(self) -> None:
        self.assertTrue(preflight.diff_touches_case_selection('+    "minimumIndependentSignals": 3'))
        self.assertTrue(preflight.diff_touches_case_selection('+    "exactScopes": ['))
        self.assertTrue(preflight.diff_touches_case_selection('+    "negativeSignals": ['))
        self.assertFalse(preflight.diff_touches_case_selection('+    "sha256": "abc"'))


class CasePythonScanPathTests(unittest.TestCase):
    def test_helper_python_file_is_scanned(self) -> None:
        path = preflight.CASES_ROOT / "iv8" / "demo" / "lib" / "helper.py"
        self.assertTrue(preflight.is_case_python_scan_path(path))

    def test_case_test_python_file_is_not_scanned(self) -> None:
        path = preflight.CASES_ROOT / "iv8" / "demo" / "tests" / "test_vectors.py"
        self.assertFalse(preflight.is_case_python_scan_path(path))

    def test_live_state_selector_is_not_entry_scanned(self) -> None:
        path = preflight.CASES_ROOT / "iv8" / "demo" / "pull_live_state.py"
        self.assertFalse(preflight.is_case_python_scan_path(path))

    def test_nested_file_maps_to_case_root(self) -> None:
        path = preflight.CASES_ROOT / "iv8" / "demo" / "lib" / "helper.py"
        self.assertEqual("iv8/demo", preflight.case_rel_from_path(path))


if __name__ == "__main__":
    unittest.main()
