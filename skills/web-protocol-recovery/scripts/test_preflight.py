import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("preflight", SCRIPT_DIR / "preflight.py")
assert SPEC is not None
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(preflight)


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


class PreflightSelfTestGateTests(unittest.TestCase):
    def test_missing_self_test_file_fails_closed(self) -> None:
        missing = preflight.SKILL_ROOT / "scripts" / "test_preflight.py"
        with mock.patch.object(Path, "is_file", return_value=False):
            ok, out = preflight.check_preflight_unit_tests()
        self.assertFalse(ok)
        self.assertIn("MISSING", out)
        self.assertTrue(missing.name.endswith("test_preflight.py"))

    def test_skip_tests_still_runs_self_tests(self) -> None:
        with (
            mock.patch.object(preflight, "check_hashes", return_value=(True, "hash ok")),
            mock.patch.object(preflight, "scan_entries", return_value=[]),
            mock.patch.object(
                preflight,
                "check_preflight_unit_tests",
                return_value=(True, "self tests ok"),
            ) as self_tests,
            mock.patch.object(preflight, "discover_test_cases") as discover,
            mock.patch.object(preflight, "check_case_tests") as case_tests,
            redirect_stdout(io.StringIO()),
        ):
            code = preflight.main(["--skip-tests"])
        self.assertEqual(0, code)
        self_tests.assert_called_once()
        discover.assert_not_called()
        case_tests.assert_not_called()


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


if __name__ == "__main__":
    unittest.main()
