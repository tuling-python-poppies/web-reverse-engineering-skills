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
        offender = validate_architecture.SKILL_ROOT / "references" / "providers" / "implementation" / "iv8" / "references" / "api-examples" / "network_bridge.py"

        self.assertEqual(validate_architecture.python_live_egress_findings(offender), [])


if __name__ == "__main__":
    unittest.main()
