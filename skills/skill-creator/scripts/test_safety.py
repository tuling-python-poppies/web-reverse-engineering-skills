#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Regression tests for skill-creator change control and packaging safety."""

import argparse
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.change_control import allowed_state_hash, append_ledger, check, file_hash, restore, snapshot
from scripts.change_control import readonly_state_hash, verify_readonly
from scripts.aggregate_benchmark import aggregate_results, load_run_results, validate_grading
from scripts.create_review_manifest import create_manifest
from scripts.package_skill import package_skill
from scripts.run_loop import conservative_accuracy, prompt_regressions, run_loop, split_eval_set

improve_description_script = importlib.import_module("scripts.improve_description")
run_eval_script = importlib.import_module("scripts.run_eval")
run_loop_script = importlib.import_module("scripts.run_loop")


SKILL_MD = "---\nname: fixture\ndescription: fixture skill\n---\n"


class ChangeControlTests(unittest.TestCase):
    def make_fixture(self, base: Path):
        root = base / "fixture"
        root.mkdir()
        (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        (root / "allowed.txt").write_text("baseline", encoding="utf-8")
        manifest = base / "control.json"
        args = argparse.Namespace(
            confirm=True,
            skill_path=str(root),
            manifest=str(manifest),
            allow=["allowed.txt", "created.txt"],
        )
        self.assertEqual(snapshot(args), 0)
        return root, manifest

    def test_restore_only_touches_allowlisted_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_fixture(Path(temp_dir))
            (root / "allowed.txt").write_text("changed", encoding="utf-8")
            (root / "created.txt").write_text("created", encoding="utf-8")
            (root / "concurrent.txt").write_text("keep", encoding="utf-8")

            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, ["allowed.txt", "created.txt"]),
            )
            self.assertEqual(restore(args), 0)
            self.assertEqual((root / "allowed.txt").read_text(encoding="utf-8"), "baseline")
            self.assertFalse((root / "created.txt").exists())
            self.assertEqual((root / "concurrent.txt").read_text(encoding="utf-8"), "keep")

    def test_tampered_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_fixture(Path(temp_dir))
            archive = manifest.with_suffix(".baseline.zip")
            archive.write_bytes(archive.read_bytes() + b"tampered")
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, ["allowed.txt", "created.txt"]),
            )
            self.assertEqual(restore(args), 2)

    def test_restore_rejects_concurrent_allowlisted_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_fixture(Path(temp_dir))
            expected = allowed_state_hash(root, ["allowed.txt", "created.txt"])
            (root / "allowed.txt").write_text("concurrent", encoding="utf-8")
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=expected,
            )
            self.assertEqual(restore(args), 2)

    def test_check_rejects_unapproved_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_fixture(Path(temp_dir))
            (root / "other.txt").write_text("unexpected", encoding="utf-8")
            args = argparse.Namespace(skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest))
            self.assertEqual(check(args), 1)

    def make_missing_target_fixture(self, base: Path):
        repo = base / "repo"
        skills = repo / "skills"
        skills.mkdir(parents=True)
        (repo / "outside.txt").write_text("outside", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "outside.txt"], cwd=repo, check=True)
        root = skills / "new-skill"
        manifest = base / "missing-control.json"
        args = argparse.Namespace(
            confirm=True,
            skill_path=str(root),
            manifest=str(manifest),
            allow=["SKILL.md", "references/guide.md"],
            ledger=[],
            allow_missing_target=True,
        )
        self.assertEqual(snapshot(args), 0)
        return root, manifest

    def test_missing_target_snapshot_restores_only_new_skill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_missing_target_fixture(Path(temp_dir))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertFalse(data["skill_root_existed"])
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (root / "references").mkdir()
            (root / "references" / "guide.md").write_text("guide", encoding="utf-8")
            check_args = argparse.Namespace(
                skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest), expected_state=None
            )
            self.assertEqual(check(check_args), 0)
            restore_args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, data["allowed_paths"]),
            )
            self.assertEqual(restore(restore_args), 0)
            self.assertFalse(root.exists())

    def test_missing_target_restore_rejects_unapproved_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_missing_target_fixture(Path(temp_dir))
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (root / "concurrent.txt").write_text("keep", encoding="utf-8")
            data = json.loads(manifest.read_text(encoding="utf-8"))
            restore_args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, data["allowed_paths"]),
            )
            self.assertEqual(restore(restore_args), 2)
            self.assertTrue((root / "SKILL.md").is_file())
            self.assertEqual((root / "concurrent.txt").read_text(encoding="utf-8"), "keep")

    def test_missing_target_restore_rejects_unapproved_empty_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root, manifest = self.make_missing_target_fixture(Path(temp_dir))
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (root / "concurrent-empty").mkdir()
            data = json.loads(manifest.read_text(encoding="utf-8"))
            restore_args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, data["allowed_paths"]),
            )
            self.assertEqual(restore(restore_args), 2)
            self.assertTrue((root / "SKILL.md").is_file())
            self.assertTrue((root / "concurrent-empty").is_dir())

    def test_missing_target_requires_explicit_flag_and_skill_allowlist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            skills = base / "skills"
            skills.mkdir()
            root = skills / "new-skill"
            manifest = base / "control.json"
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                allow=["SKILL.md"],
                ledger=[],
                allow_missing_target=False,
            )
            self.assertEqual(snapshot(args), 2)
            self.assertFalse(manifest.exists())
            args.allow_missing_target = True
            args.allow = ["README.md"]
            self.assertEqual(snapshot(args), 2)
            self.assertFalse(manifest.exists())

    def test_collect_exclusions_are_relative_to_skill_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir) / "node_modules"
            root = base / "fixture"
            root.mkdir(parents=True)
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            manifest = Path(temp_dir) / "control.json"
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                allow=["SKILL.md"],
                ledger=[],
            )
            self.assertEqual(snapshot(args), 0)
            (root / "other.txt").write_text("unexpected", encoding="utf-8")
            check_args = argparse.Namespace(
                skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest), expected_state=None
            )
            self.assertEqual(check(check_args), 1)

    def test_hard_linked_skill_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            protected = base / "protected.txt"
            protected.write_text("protected", encoding="utf-8")
            os.link(protected, root / "allowed.txt")
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(base / "control.json"),
                allow=["allowed.txt"],
                ledger=[],
            )
            self.assertEqual(snapshot(args), 2)
            self.assertEqual(protected.read_text(encoding="utf-8"), "protected")

    @unittest.skipUnless(os.path.normcase("A") == os.path.normcase("a"), "case-insensitive filesystem behavior")
    def test_existing_allowlist_case_is_canonicalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (root / "Allowed.txt").write_text("baseline", encoding="utf-8")
            manifest = base / "control.json"
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                allow=["allowed.txt"],
                ledger=[],
            )
            self.assertEqual(snapshot(args), 0)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["allowed_paths"], ["Allowed.txt"])
            (root / "Allowed.txt").write_text("candidate", encoding="utf-8")
            restore_args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, data["allowed_paths"]),
            )
            self.assertEqual(restore(restore_args), 0)
            self.assertEqual((root / "Allowed.txt").read_text(encoding="utf-8"), "baseline")

    @unittest.skipUnless(os.path.normcase("A") == os.path.normcase("a"), "case-insensitive filesystem behavior")
    def test_excluded_allowlist_case_is_canonicalized_and_archived(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            excluded = root / "node_modules"
            excluded.mkdir(parents=True)
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (excluded / "Allowed.txt").write_text("baseline", encoding="utf-8")
            manifest = base / "control.json"
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                allow=["node_modules/allowed.txt"],
                ledger=[],
            )
            self.assertEqual(snapshot(args), 0)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            canonical = str(Path("node_modules") / "Allowed.txt")
            self.assertEqual(data["allowed_paths"], [canonical])
            self.assertEqual(data["baseline_allowed_files"][canonical], file_hash(excluded / "Allowed.txt"))
            (excluded / "Allowed.txt").write_text("candidate", encoding="utf-8")
            restore_args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                expected_state=allowed_state_hash(root, data["allowed_paths"]),
            )
            self.assertEqual(restore(restore_args), 0)
            self.assertEqual((excluded / "Allowed.txt").read_text(encoding="utf-8"), "baseline")

    def make_git_fixture(self, base: Path):
        repo = base / "repo"
        root = repo / "fixture"
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        (root / "allowed.txt").write_text("baseline", encoding="utf-8")
        (repo / "outside.txt").write_text("outside", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        manifest = repo / "control.json"
        ledger = repo / "ledger.tsv"
        args = argparse.Namespace(
            confirm=True,
            skill_path=str(root),
            manifest=str(manifest),
            allow=["allowed.txt"],
            ledger=[str(ledger)],
        )
        self.assertEqual(snapshot(args), 0)
        return repo, root, manifest, ledger

    def test_git_guard_detects_outside_worktree_and_index_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo, root, manifest, _ = self.make_git_fixture(Path(temp_dir))
            (repo / "outside.txt").write_text("dirty", encoding="utf-8")
            args = argparse.Namespace(skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest), expected_state=None)
            self.assertEqual(check(args), 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo, root, manifest, _ = self.make_git_fixture(Path(temp_dir))
            (repo / "outside.txt").write_text("dirty", encoding="utf-8")
            # Capture a second baseline with an already-dirty file, then change only its index state.
            manifest.unlink()
            manifest.with_suffix(".baseline.zip").unlink()
            snap_args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(manifest),
                allow=["allowed.txt"],
                ledger=[],
            )
            self.assertEqual(snapshot(snap_args), 0)
            subprocess.run(["git", "add", "outside.txt"], cwd=repo, check=True)
            args = argparse.Namespace(skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest), expected_state=None)
            self.assertEqual(check(args), 1)

    def test_ledger_expected_state_detects_concurrent_append(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, root, manifest, ledger = self.make_git_fixture(Path(temp_dir))
            state = allowed_state_hash(root, ["allowed.txt"], [str(ledger)])
            ledger.write_text("concurrent\n", encoding="utf-8")
            args = argparse.Namespace(skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest), expected_state=state)
            self.assertEqual(check(args), 2)

    def test_manifest_tamper_downgrade_and_allowed_staging_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo, root, manifest, _ = self.make_git_fixture(Path(temp_dir))
            digest = file_hash(manifest)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["allowed_paths"].append("SKILL.md")
            manifest.write_text(json.dumps(data), encoding="utf-8")
            args = argparse.Namespace(skill_path=str(root), manifest=str(manifest), manifest_sha256=digest, expected_state=None)
            self.assertEqual(check(args), 2)

            data["version"] = 1
            manifest.write_text(json.dumps(data), encoding="utf-8")
            args.manifest_sha256 = file_hash(manifest)
            self.assertEqual(check(args), 2)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo, root, manifest, _ = self.make_git_fixture(Path(temp_dir))
            (root / "allowed.txt").write_text("candidate", encoding="utf-8")
            subprocess.run(["git", "add", "fixture/allowed.txt"], cwd=repo, check=True)
            args = argparse.Namespace(
                skill_path=str(root), manifest=str(manifest), manifest_sha256=file_hash(manifest), expected_state=None
            )
            self.assertEqual(check(args), 1)

    def test_guarded_ledger_append_updates_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, root, manifest, ledger = self.make_git_fixture(Path(temp_dir))
            initial = allowed_state_hash(root, ["allowed.txt"], [str(ledger)])
            args = argparse.Namespace(
                skill_path=str(root),
                manifest=str(manifest),
                manifest_sha256=file_hash(manifest),
                ledger=str(ledger),
                expected_state=initial,
                line="row-1",
            )
            self.assertEqual(append_ledger(args), 0)
            self.assertEqual(ledger.read_text(encoding="utf-8"), "row-1\n")

    def test_hard_linked_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (root / "allowed.txt").write_text("baseline", encoding="utf-8")
            protected = base / "protected.tsv"
            protected.write_text("protected\n", encoding="utf-8")
            ledger = base / "ledger.tsv"
            os.link(protected, ledger)
            args = argparse.Namespace(
                confirm=True,
                skill_path=str(root),
                manifest=str(base / "control.json"),
                allow=["allowed.txt"],
                ledger=[str(ledger)],
            )
            self.assertEqual(snapshot(args), 2)
            self.assertEqual(protected.read_text(encoding="utf-8"), "protected\n")

    def test_readonly_fingerprint_detects_changes_without_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.txt").write_text("a", encoding="utf-8")
            state = readonly_state_hash(root)
            args = argparse.Namespace(root=str(root), expected_state=state)
            self.assertEqual(verify_readonly(args), 0)
            (root / "a.txt").write_text("b", encoding="utf-8")
            self.assertEqual(verify_readonly(args), 1)


class PackageTests(unittest.TestCase):
    def test_package_is_exclusive_and_excludes_local_evals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (root / "test-prompts.json").write_text("[]", encoding="utf-8")
            output = base / "dist"
            archive = package_skill(root, output)
            self.assertIsNotNone(archive)
            assert archive is not None
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            self.assertTrue(any(name.endswith("SKILL.md") for name in names))
            self.assertFalse(any(name.endswith("test-prompts.json") for name in names))
            self.assertIsNone(package_skill(root, output))

    def test_output_inside_skill_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "fixture"
            root.mkdir()
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            output = root / "dist"
            self.assertIsNone(package_skill(root, output))
            self.assertFalse(output.exists())


class BenchmarkIntegrityTests(unittest.TestCase):
    def make_run(self, root: Path, config: str, reviewer: str = "grader-agent"):
        eval_dir = root / "eval-1"
        eval_dir.mkdir(exist_ok=True)
        metadata = {
            "eval_id": 1,
            "eval_name": "fixture",
            "eval_mode": "executed",
            "executor_id": "executor-agent",
            "expectations": ["The output is complete"],
        }
        (eval_dir / "eval_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        run_dir = eval_dir / config
        outputs = run_dir / "outputs"
        outputs.mkdir(parents=True)
        (run_dir / "transcript.md").write_text("execution transcript", encoding="utf-8")
        (outputs / "result.txt").write_text("complete", encoding="utf-8")
        grading = {
            "expectations": [{"text": "The output is complete", "passed": True, "evidence": "result.txt"}],
            "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0},
        }
        (run_dir / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
        create_manifest(run_dir, reviewer)
        return run_dir

    def test_verified_primary_and_baseline_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_run(root, "with_skill")
            self.make_run(root, "without_skill")
            results = load_run_results(root)
            summary = aggregate_results(results)
            self.assertEqual(summary["delta"]["baseline"], "without_skill")
            self.assertTrue(all(run["review_verified"] for runs in results.values() for run in runs))

    def test_missing_review_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self.make_run(root, "with_skill")
            (run_dir / "review_manifest.json").unlink()
            with self.assertRaisesRegex(ValueError, "review_manifest"):
                load_run_results(root)

    def test_unmanifested_output_and_case_variant_self_review_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self.make_run(root, "with_skill")
            (run_dir / "outputs" / "late.txt").write_text("not reviewed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact set"):
                load_run_results(root)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "independent"):
                self.make_run(root, "with_skill", reviewer=" EXECUTOR-AGENT ")

    def test_nan_pass_rate_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            grading_file = Path(temp_dir) / "grading.json"
            grading = {
                "expectations": [{"text": "complete", "passed": True, "evidence": "result"}],
                "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": float("nan")},
            }
            with self.assertRaisesRegex(ValueError, "summary"):
                validate_grading(grading, grading_file)

    def test_missing_baseline_and_self_review_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_run(root, "with_skill")
            with self.assertRaisesRegex(ValueError, "baseline"):
                aggregate_results(load_run_results(root))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "independent"):
                self.make_run(root, "with_skill", reviewer="executor-agent")

    def test_secret_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            references = root / "references"
            references.mkdir(parents=True)
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            token = "sk-" + "a" * 32
            (references / "notes.txt").write_text(f"token={token}\n", encoding="utf-8")

            output = base / "dist"
            self.assertIsNone(package_skill(root, output))
            self.assertFalse(output.exists())

    def test_raw_capture_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "fixture"
            references = root / "references"
            references.mkdir(parents=True)
            (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
            (references / "session.har").write_text("{}", encoding="utf-8")

            output = base / "dist"
            self.assertIsNone(package_skill(root, output))
            self.assertFalse(output.exists())

    def test_binary_prefix_headers_and_benchmark_artifacts_are_scanned(self):
        cases = [
            ("notes.bin", b"\x00-----BEGIN " + b"PRIVATE KEY-----\nsecret"),
            ("notes.txt", b"Author" + b"ization: Bearer reusable-secret"),
            ("transcript.md", b"redacted transcript"),
            ("utf16.txt", ("sk-" + "a" * 32).encode("utf-16-le")),
        ]
        for filename, content in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp_dir:
                base = Path(temp_dir)
                root = base / "fixture"
                references = root / "references"
                references.mkdir(parents=True)
                (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
                (references / filename).write_bytes(content)
                self.assertIsNone(package_skill(root, base / "dist"))


class SubprocessIsolationTests(unittest.TestCase):
    def test_eval_uses_isolated_workspace_filtered_env_and_read_only_config(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            config_path = Path(kwargs["env"]["XDG_CONFIG_HOME"]) / "opencode" / "opencode.json"
            captured["config"] = json.loads(config_path.read_text(encoding="utf-8"))
            event = {
                "type": "tool_use",
                "part": {"tool": "skill", "state": {"input": {"name": "fixture"}}},
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(event), "")

        source_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "OPENAI_API_KEY": "must-not-leak",
            "SECRET_TOKEN": "must-not-leak",
            "OPENCODE_CONFIG_CONTENT": "must-not-leak",
        }
        with patch.dict(os.environ, source_env, clear=True), patch.object(
            run_eval_script.subprocess, "run", side_effect=fake_run
        ):
            triggered = run_eval_script.run_single_query(
                "test query", "fixture", "fixture description", 30, "C:\\real-project"
            )

        self.assertTrue(triggered)
        cmd = captured["cmd"]
        kwargs = captured["kwargs"]
        self.assertIn("--pure", cmd)
        self.assertEqual(cmd[-2:], ["--", "test query"])
        self.assertNotIn("C:\\real-project", cmd)
        self.assertEqual(cmd[cmd.index("--dir") + 1], kwargs["cwd"])
        self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
        self.assertNotIn("SECRET_TOKEN", kwargs["env"])
        self.assertNotIn("OPENCODE_CONFIG_CONTENT", kwargs["env"])
        self.assertNotEqual(kwargs["env"].get("USERPROFILE"), source_env.get("USERPROFILE"))
        self.assertTrue(all(key in kwargs["env"] for key in ("XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME")))
        self.assertEqual(
            captured["config"]["permission"],
            {"*": "deny", "skill": {"*": "deny", "fixture": "allow"}},
        )

    def test_eval_rejects_path_skill_names_and_terminates_cli_options(self):
        with self.assertRaisesRegex(ValueError, "invalid skill name"):
            run_eval_script.run_single_query("query", "..\\outside", "description", 30, "unused")

        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, "", "")
        with patch.object(run_eval_script.subprocess, "run", side_effect=fake_run):
            run_eval_script.run_single_query("--help", "fixture", "description", 30, "unused")
        self.assertEqual(captured["cmd"][-2:], ["--", "--help"])

    def test_history_optimizer_has_no_tool_permissions(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            config_path = Path(kwargs["env"]["XDG_CONFIG_HOME"]) / "opencode" / "opencode.json"
            captured["config"] = json.loads(config_path.read_text(encoding="utf-8"))
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            event = {"type": "text", "part": {"text": "answer", "metadata": {}}}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(event), "")

        with patch.dict(os.environ, {"PATH": os.environ.get("PATH", ""), "SECRET_TOKEN": "hidden"}, clear=True), patch.object(
            improve_description_script.subprocess, "run", side_effect=fake_run
        ):
            result = improve_description_script._call_opencode("history prompt", None)

        self.assertEqual(result, "answer")
        self.assertIn("--pure", captured["cmd"])
        self.assertEqual(captured["cmd"][-2:], ["--", "history prompt"])
        self.assertEqual(captured["config"]["permission"], {"*": "deny"})
        self.assertNotIn("SECRET_TOKEN", captured["kwargs"]["env"])
        self.assertEqual(
            captured["cmd"][captured["cmd"].index("--dir") + 1],
            captured["kwargs"]["cwd"],
        )


class SelectionTests(unittest.TestCase):
    def test_wilson_bound_preserves_uncertainty(self):
        results = [{"query": "a", "should_trigger": True, "triggers": 3, "runs": 3, "pass": True}]
        accuracy, lower_bound, samples = conservative_accuracy(results)
        self.assertEqual((accuracy, samples), (1.0, 3))
        self.assertLess(lower_bound, 1.0)

    def test_prompt_regression_is_detected(self):
        baseline = [{"query": "a", "pass": True}]
        candidate = [{"query": "a", "pass": False}]
        self.assertEqual(prompt_regressions(baseline, candidate), ["a"])

    def test_invalid_holdout_and_tiny_split_are_rejected(self):
        with self.assertRaises(ValueError):
            split_eval_set([], 0.0)
        with self.assertRaises(ValueError):
            split_eval_set([], 1.0)
        tiny = [
            {"query": "yes", "should_trigger": True},
            {"query": "no", "should_trigger": False},
        ]
        with self.assertRaises(ValueError):
            split_eval_set(tiny, 0.5)
        duplicate = [
            {"query": "same", "should_trigger": True},
            {"query": "yes", "should_trigger": True},
            {"query": "same", "should_trigger": False},
            {"query": "no", "should_trigger": False},
        ]
        with self.assertRaisesRegex(ValueError, "unique"):
            split_eval_set(duplicate, 0.5)

    def test_run_loop_rejects_self_evaluation(self):
        with self.assertRaisesRegex(ValueError, "holdout"):
            run_loop(
                eval_set=[],
                skill_path=Path("unused"),
                description_override=None,
                num_workers=1,
                timeout=30,
                max_iterations=1,
                runs_per_query=2,
                trigger_threshold=0.5,
                holdout=0.0,
                model="provider/model",
                verbose=False,
            )

    def test_holdout_is_only_evaluated_after_train_selection(self):
        eval_set = [
            {"query": "yes-a", "should_trigger": True},
            {"query": "yes-b", "should_trigger": True},
            {"query": "no-a", "should_trigger": False},
            {"query": "no-b", "should_trigger": False},
        ]
        calls = []

        def fake_eval(eval_set, description, runs_per_query, **kwargs):
            calls.append((description, {item["query"] for item in eval_set}))
            results = []
            for index, item in enumerate(eval_set):
                correct = description == "candidate" or index > 0
                should_trigger = item["should_trigger"]
                triggers = runs_per_query if should_trigger == correct else 0
                results.append({
                    "query": item["query"],
                    "should_trigger": should_trigger,
                    "triggers": triggers,
                    "runs": runs_per_query,
                    "pass": correct,
                })
            passed = sum(1 for item in results if item["pass"])
            return {"results": results, "summary": {"passed": passed, "failed": len(results) - passed, "total": len(results)}}

        with patch.object(run_loop_script, "parse_skill_md", return_value=("fixture", "baseline", "content")), patch.object(
            run_loop_script, "find_project_root", return_value=Path("isolated-by-run-eval")
        ), patch.object(run_loop_script, "run_eval", side_effect=fake_eval), patch.object(
            run_loop_script, "improve_description", return_value="candidate"
        ):
            output = run_loop(
                eval_set=eval_set,
                skill_path=Path("unused"),
                description_override=None,
                num_workers=1,
                timeout=30,
                max_iterations=2,
                runs_per_query=2,
                trigger_threshold=0.5,
                holdout=0.5,
                model="provider/model",
                verbose=False,
            )

        self.assertEqual(len(calls), 4)
        train_queries = calls[0][1]
        holdout_queries = calls[2][1]
        self.assertEqual(calls[1][1], train_queries)
        self.assertEqual(calls[3][1], holdout_queries)
        self.assertTrue(train_queries.isdisjoint(holdout_queries))
        self.assertEqual(train_queries | holdout_queries, {item["query"] for item in eval_set})
        self.assertEqual(output["best_description"], "candidate")


if __name__ == "__main__":
    unittest.main()
