import importlib.util
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
