#!/usr/bin/env python3
"""Focused architecture acceptance contract tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_case_registry
import validate_architecture
import verify_case_hashes


def row(case_id: str, signals: list[str], negatives: list[str]) -> dict:
    return {
        "caseId": case_id,
        "family": "signer",
        "exactScopes": [{"scheme": "https", "host": "api.example.test", "port": 443, "routePrefix": "/api"}],
        "match": {"signals": signals, "negativeSignals": negatives},
    }


class ArchitectureContractTests(unittest.TestCase):
    def test_unresolvable_source_reference_is_explicitly_bounded(self) -> None:
        path = (
            validate_architecture.SKILL_ROOT
            / "references"
            / "cases"
            / "python-node"
            / "universal-vmp-instrumentation"
            / "case.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            verify_case_hashes.source_provenance_findings(
                validate_architecture.SKILL_ROOT, "fixture", data
            ),
            [],
        )

    def test_short_source_reference_cannot_claim_source_commit(self) -> None:
        data = {
            "verificationClass": "historical-user-attested",
            "verification": {"sourceCommit": "95be929~1"},
        }
        findings = verify_case_hashes.source_provenance_findings(
            validate_architecture.SKILL_ROOT, "fixture", data
        )
        self.assertTrue(any("full commit id" in finding for finding in findings))

    def test_resolvable_reference_must_be_recorded_as_commit(self) -> None:
        data = {
            "verificationClass": "historical-user-attested",
            "verification": {
                "sourceReference": "HEAD",
                "sourceReferenceResolution": {
                    "status": "unresolvable-in-current-repository",
                    "checkedAt": "2026-07-31T14:34:34+08:00",
                    "reason": "fixture",
                },
            },
        }
        findings = verify_case_hashes.source_provenance_findings(
            validate_architecture.SKILL_ROOT, "fixture", data
        )
        self.assertTrue(any("resolves and must be recorded" in finding for finding in findings))

    def test_inherited_camoufox_current_stage_is_rejected(self) -> None:
        """Copying a historical camoufox stage into the current chain must fail.

        This is the exact defect that shipped: four python-node cases duplicated
        historicalProviderChain into requiredCurrentProviderChain, so a signal
        match handed the model a camoufox order the hub forbids.
        """
        findings = validate_architecture.current_camoufox_findings(
            "fixture",
            [{"provider": "camoufox", "role": "reconnaissance"}],
        )
        self.assertTrue(any("without a camoufoxCriterion" in item for item in findings))

    def test_declared_camoufox_criterion_is_accepted(self) -> None:
        findings = validate_architecture.current_camoufox_findings(
            "fixture",
            [
                {
                    "provider": "camoufox",
                    "role": "reconnaissance",
                    "camoufoxCriterion": "engine-level SpiderMonkey property tracing",
                }
            ],
        )
        self.assertEqual(findings, [])

    def test_historical_camoufox_stage_stays_legal(self) -> None:
        """Only the current chain is gated; provenance must remain recordable."""
        for path in sorted(validate_architecture.CASES_ROOT.glob("**/case.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            historical = data.get("historicalProviderChain") or []
            if any(stage.get("provider") == "camoufox" for stage in historical):
                self.assertEqual(
                    validate_architecture.current_camoufox_findings(
                        str(data.get("caseId")),
                        data.get("requiredCurrentProviderChain") or [],
                    ),
                    [],
                )
                return
        self.fail("expected at least one case with a historical camoufox stage")

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

    def test_case_live_reference_archive_is_study_only(self) -> None:
        archive = validate_architecture.SKILL_ROOT / "references" / "case-live-reference-archive"
        with tempfile.TemporaryDirectory(dir=archive) as tmp:
            path = Path(tmp) / "entry.py"
            path.write_text(
                "import requests\n\ndef main():\n    requests.get('https://example.com')\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_architecture.python_live_egress_findings(path), [])

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

    def test_reese84_signal_groups_are_disjoint_and_declared(self) -> None:
        match = {
            "signals": ["cookie:reese84", "challenge:randomized-path"],
            "minimumIndependentSignals": 2,
            "requiredSignalGroups": [
                {"name": "reese84-native", "anyOf": ["cookie:reese84"]},
                {
                    "name": "independent-corroboration",
                    "anyOf": ["challenge:randomized-path"],
                },
            ],
        }
        self.assertEqual(
            validate_architecture.required_signal_group_findings(
                "reese84-case",
                match,
                {"reese84-native", "independent-corroboration"},
            ),
            [],
        )

    def test_reese84_vendor_labels_cannot_fill_both_groups(self) -> None:
        match = {
            "signals": ["vendor:imperva", "vendor:reese84"],
            "minimumIndependentSignals": 2,
            "requiredSignalGroups": [
                {"name": "reese84-native", "anyOf": ["vendor:imperva"]},
                {
                    "name": "independent-corroboration",
                    "anyOf": ["vendor:reese84"],
                },
            ],
        }
        findings = validate_architecture.required_signal_group_findings(
            "reese84-case",
            match,
            {"reese84-native", "independent-corroboration"},
        )
        self.assertTrue(any("labels cannot satisfy" in finding for finding in findings))

    def test_gt4_nine_grid_requires_native_subtype_groups(self) -> None:
        match = {
            "signals": [
                "request:risk_type-nine",
                "response:captcha_type-nine",
                "response:imgs-ques-nine_nums",
            ],
            "minimumIndependentSignals": 3,
            "requiredSignalGroups": [
                {
                    "name": "gt4-request-subtype",
                    "anyOf": ["request:risk_type-nine"],
                },
                {
                    "name": "gt4-response-subtype",
                    "anyOf": ["response:captcha_type-nine"],
                },
                {
                    "name": "nine-grid-shape",
                    "anyOf": ["response:imgs-ques-nine_nums"],
                },
            ],
        }
        self.assertEqual(
            validate_architecture.required_signal_group_findings(
                "gt4-nine-grid",
                match,
                {
                    "gt4-request-subtype",
                    "gt4-response-subtype",
                    "nine-grid-shape",
                },
            ),
            [],
        )

    def test_large_pytorch_asset_requires_read_and_execution_contracts(self) -> None:
        good = {
            "assets": [
                {
                    "path": "assets/model.pt",
                    "bytes": validate_architecture.LARGE_ASSET_STORAGE_POLICY_BYTES,
                    "readHint": "Do not deserialize during inspection.",
                    "storagePolicy": "regular-git-self-contained",
                    "serializationRisk": "executable-pickle",
                    "executionPolicy": "explicit-opt-in-after-hash-verification",
                }
            ]
        }
        self.assertEqual(
            validate_architecture.case_asset_contract_findings("model-case", good),
            [],
        )
        bad = {
            "assets": [
                {
                    "path": "assets/model.pt",
                    "bytes": validate_architecture.LARGE_ASSET_STORAGE_POLICY_BYTES,
                }
            ]
        }
        findings = validate_architecture.case_asset_contract_findings("model-case", bad)
        self.assertEqual(len(findings), 4)
        self.assertTrue(any("readHint" in finding for finding in findings))
        self.assertTrue(any("storagePolicy" in finding for finding in findings))
        self.assertTrue(any("serializationRisk" in finding for finding in findings))
        self.assertTrue(any("executionPolicy" in finding for finding in findings))

    def test_case_process_rejects_default_secret_storage_and_provider_root(self) -> None:
        findings = validate_architecture.case_process_policy_findings(
            "fixture",
            "Persist `js_reverse_cache/pzds_session.json` and use `verifier/t001_profile.json`.\n"
            "Keep full request/response bodies.",
        )
        self.assertTrue(any("session/token/cookie" in item for item in findings))
        self.assertTrue(any("verifier/ project root" in item for item in findings))
        self.assertTrue(any("raw request/response" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
