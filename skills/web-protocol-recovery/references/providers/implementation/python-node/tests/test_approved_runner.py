from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from approved_runner import ApprovedArtifactRunner, ApprovedRunnerError


class Adapter:
    capability_denied = True
    adapter_id = "adapter"
    adapter_sha256 = "b" * 64

    def __init__(self) -> None:
        self.closed = False

    def execute(self, operation, payload, policy):
        if operation == "data_builder":
            return {"output": "encoded"}
        return {"sign": "s", "timestamp": "1", "random": "2"}

    def close(self):
        self.closed = True


class ApprovedRunnerTests(unittest.TestCase):
    def work_order(self, asset_hash: str) -> dict:
        return {
            "authorization": {
                "executionPolicy": {
                    "targetCodeExecution": "approved-reviewed-hash",
                    "approvedCodeSha256": [asset_hash],
                    "approvalDeadline": "2099-01-01T00:00:00Z",
                    "sandbox": {
                        "backend": "capability-denied-external",
                        "adapterId": "adapter",
                        "adapterSha256": "b" * 64,
                        "capabilityEvidence": "no-network-no-filesystem",
                        "timeoutMs": 1000,
                        "outputByteCap": 1024,
                    },
                }
            }
        }

    def test_hash_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "asset.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            adapter = Adapter()
            runner = ApprovedArtifactRunner(self.work_order(digest), {"asset.js": asset}, adapter)
            self.assertEqual(runner.execute("data_builder", {"input": "x"}), {"output": "encoded"})
            with self.assertRaises(ApprovedRunnerError):
                runner.execute("network", {})
            runner.close()
            self.assertTrue(adapter.closed)

    def test_missing_capability_attestation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "asset.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            adapter = Adapter()
            adapter.capability_denied = False
            with self.assertRaises(ApprovedRunnerError):
                ApprovedArtifactRunner(self.work_order(digest), {"asset.js": asset}, adapter)
