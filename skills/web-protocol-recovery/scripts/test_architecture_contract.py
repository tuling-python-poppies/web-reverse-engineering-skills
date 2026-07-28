#!/usr/bin/env python3
"""Focused architecture acceptance contract tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import build_case_registry
import validate_architecture


def row(case_id: str, signals: list[str], negatives: list[str]) -> dict:
    return {
        "caseId": case_id,
        "family": "signer",
        "exactScopes": [{"scheme": "https", "host": "api.example.test", "port": 443, "routePrefix": "/api"}],
        "match": {"signals": signals, "negativeSignals": negatives},
    }


class ArchitectureContractTests(unittest.TestCase):
    def test_case_ambiguity_requires_negative_discriminator(self) -> None:
        left = row("left", ["parameter:s"], [])
        right = row("right", ["parameter:s"], [])
        findings = build_case_registry.ambiguity_findings([left, right])
        self.assertEqual(len(findings), 1)
        self.assertIn("left <-> right", findings[0])

    def test_case_ambiguity_accepts_cross_negative_signal(self) -> None:
        left = row("left", ["runtime:iv8"], ["runtime:pure-python"])
        right = row("right", ["runtime:pure-python"], ["runtime:iv8"])
        self.assertEqual(build_case_registry.ambiguity_findings([left, right]), [])

    def test_live_egress_scan_covers_provider_api_examples(self) -> None:
        offender = (
            validate_architecture.SKILL_ROOT
            / "references"
            / "providers"
            / "implementation"
            / "iv8"
            / "references"
            / "api-examples"
            / "network_bridge.py"
        )
        self.assertEqual(validate_architecture.python_live_egress_findings(offender), [])

    def test_case_live_http_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory(dir=validate_architecture.SKILL_ROOT) as tmp:
            path = Path(tmp) / "entry.py"
            path.write_text(
                "import requests\n\ndef main():\n    requests.get('https://example.com')\n",
                encoding="utf-8",
            )
            findings = validate_architecture.python_live_egress_findings(path)
            self.assertTrue(findings)
            self.assertIn("non-delivery live HTTP", findings[0])

    def test_current_case_entries_are_offline(self) -> None:
        path = (
            validate_architecture.SKILL_ROOT
            / "references"
            / "cases"
            / "iv8"
            / "jd-h5st"
            / "entry.py"
        )
        self.assertEqual(validate_architecture.python_live_egress_findings(path), [])

    def test_signal_ambiguity_without_scope_is_detected(self) -> None:
        left = {
            "caseId": "left",
            "family": "signer",
            "exactScopes": [],
            "match": {
                "signals": ["parameter:s", "sdk:webmssdk"],
                "minimumIndependentSignals": 2,
                "negativeSignals": [],
            },
        }
        right = {
            "caseId": "right",
            "family": "signer",
            "exactScopes": [],
            "match": {
                "signals": ["parameter:s", "sdk:webmssdk"],
                "minimumIndependentSignals": 2,
                "negativeSignals": [],
            },
        }
        findings = build_case_registry.ambiguity_findings([left, right])
        self.assertEqual(len(findings), 1)
        self.assertIn("minimum-signal set", findings[0])


if __name__ == "__main__":
    unittest.main()
