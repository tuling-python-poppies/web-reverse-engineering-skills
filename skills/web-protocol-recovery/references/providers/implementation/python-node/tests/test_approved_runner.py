from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from approved_runner import (
    ApprovedArtifactRunner,
    ApprovedProcessLauncher,
    ApprovedRunnerError,
    run_blocked_without_launcher,
)


class LauncherStub:
    def __init__(self, output: dict | None = None) -> None:
        self.output = output or {"output": "encoded"}
        self.closed = False

    def execute(self, script_path, payload, policy):
        return dict(self.output)

    def close(self):
        self.closed = True


class ApprovedRunnerTests(unittest.TestCase):
    def work_order(self, asset_hash: str, *, mode: str = "approved-reviewed-hash") -> dict:
        policy = {
            "targetCodeExecution": mode,
            "approvedCodeSha256": [asset_hash],
        }
        if mode == "approved-reviewed-hash":
            policy["approvalDeadline"] = "2099-01-01T00:00:00Z"
        return {"authorization": {"executionPolicy": policy}}

    def test_envelope_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "data_builder.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            launcher = LauncherStub()
            runner = ApprovedArtifactRunner(
                self.work_order(digest), {"data_builder.js": asset}, launcher
            )
            self.assertEqual(runner.execute("data_builder", {"input": "x"}), {"output": "encoded"})
            with self.assertRaises(ApprovedRunnerError):
                runner.execute("network", {})
            runner.close()
            self.assertTrue(launcher.closed)

    def test_hash_mismatch_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "data_builder.js"
            asset.write_text("asset", encoding="utf-8")
            with self.assertRaises(ApprovedRunnerError):
                ApprovedArtifactRunner(
                    self.work_order("a" * 64), {"data_builder.js": asset}, LauncherStub()
                )

    def test_expired_deadline_blocks_reviewed_hash_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "data_builder.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            order = self.work_order(digest)
            order["authorization"]["executionPolicy"]["approvalDeadline"] = "2020-01-01T00:00:00Z"
            with self.assertRaises(ApprovedRunnerError):
                ApprovedArtifactRunner(order, {"data_builder.js": asset}, LauncherStub())

    def test_blocked_mode_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "data_builder.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            with self.assertRaises(ApprovedRunnerError):
                ApprovedArtifactRunner(
                    self.work_order(digest, mode="blocked"),
                    {"data_builder.js": asset},
                    LauncherStub(),
                )

    def test_local_only_requires_no_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "data_builder.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            runner = ApprovedArtifactRunner(
                self.work_order(digest, mode="local-only"),
                {"data_builder.js": asset},
                LauncherStub(),
            )
            self.assertEqual(runner.execute("data_builder", {}), {"output": "encoded"})
            runner.close()

    def test_missing_launcher_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            asset = Path(temp) / "data_builder.js"
            asset.write_text("asset", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            class BrokenLauncher:
                def close(self):
                    return None

            with self.assertRaises(ApprovedRunnerError):
                ApprovedArtifactRunner(
                    self.work_order(digest), {"data_builder.js": asset}, BrokenLauncher()
                )


class ProcessLauncherTests(unittest.TestCase):
    def script(self, directory: Path, body: str, name: str = "script.py") -> Path:
        script = directory / name
        script.write_text(body, encoding="utf-8")
        return script

    def cache_dir(self, base: Path) -> Path:
        cache = base / "js_reverse_cache" / "approved"
        cache.mkdir(parents=True)
        return cache

    def test_real_subprocess_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = self.cache_dir(root)
            script = self.script(
                root,
                "import json,sys\npayload=json.loads(sys.stdin.read())\n"
                "print(json.dumps({'output': payload['input'].upper()}))",
            )
            launcher = ApprovedProcessLauncher(
                cache, node_executable=sys.executable, allowed_scripts={"script.py": script}
            )
            output = launcher.execute(script, {"input": "abc"}, {})
            self.assertEqual(output, {"output": "ABC"})
            launcher.close()

    def test_timeout_kills_and_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = self.cache_dir(root)
            script = self.script(root, "import time\ntime.sleep(10)")
            launcher = ApprovedProcessLauncher(
                cache,
                node_executable=sys.executable,
                allowed_scripts={"script.py": script},
                timeout_ms=500,
            )
            with self.assertRaises(ApprovedRunnerError):
                launcher.execute(script, {}, {})
            launcher.close()

    def test_output_cap_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = self.cache_dir(root)
            script = self.script(
                root, "import json\nprint(json.dumps({'output': 'x' * 100000}))"
            )
            launcher = ApprovedProcessLauncher(
                cache,
                node_executable=sys.executable,
                allowed_scripts={"script.py": script},
                output_byte_cap=1024,
            )
            with self.assertRaises(ApprovedRunnerError):
                launcher.execute(script, {}, {})
            launcher.close()

    def test_cwd_outside_cache_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            outside = Path(temp) / "not-cache"
            outside.mkdir()
            with self.assertRaises(ApprovedRunnerError):
                ApprovedProcessLauncher(outside)

    def test_unapproved_script_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = self.cache_dir(root)
            allowed = self.script(root, "print('{}')", name="allowed.py")
            other = self.script(root, "print('{}')", name="other.py")
            launcher = ApprovedProcessLauncher(
                cache, node_executable=sys.executable, allowed_scripts={"script.py": allowed}
            )
            with self.assertRaises(ApprovedRunnerError):
                launcher.execute(other, {}, {})
            launcher.close()

    def test_blocked_without_launcher_helper(self) -> None:
        with self.assertRaises(ApprovedRunnerError):
            run_blocked_without_launcher()


if __name__ == "__main__":
    unittest.main(verbosity=2)
