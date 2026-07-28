#!/usr/bin/env python3
"""Focused Architecture V2 acceptance contract tests."""

from __future__ import annotations

import unittest

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

    def test_case_live_requires_historical_allowlist(self) -> None:
        path = (
            validate_architecture.SKILL_ROOT
            / "references"
            / "cases"
            / "iv8"
            / "jd-h5st"
            / "entry.py"
        )
        findings = validate_architecture.python_live_egress_findings(path, allowlist=set())
        self.assertTrue(findings)
        self.assertIn("historical-live-egress.json", findings[0])

    def test_historical_case_live_allowlist_accepts_known_path(self) -> None:
        path = (
            validate_architecture.SKILL_ROOT
            / "references"
            / "cases"
            / "iv8"
            / "jd-h5st"
            / "entry.py"
        )
        allowlist = {"references/cases/iv8/jd-h5st/entry.py"}
        self.assertEqual(
            validate_architecture.python_live_egress_findings(path, allowlist=allowlist),
            [],
        )

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
