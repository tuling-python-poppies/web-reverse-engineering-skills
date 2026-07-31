from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry  # noqa: E402


class GeetestNineGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(
            (CASE_ROOT / "fixtures" / "vectors.json").read_text(encoding="utf-8")
        )

    def test_model_asset_manifest(self) -> None:
        actual = entry.verify_model_assets()
        self.assertEqual(actual, self.vectors["model"])

    def test_model_execution_proof_is_narrow_and_path_free(self) -> None:
        proof = json.loads(
            (CASE_ROOT / "fixtures" / "model-execution-proof.summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(proof["activeScope"], "local-checkpoint-smoke-only")
        self.assertTrue(proof["currentAcceptance"])
        self.assertEqual(proof["checkpoint"]["sha256"], self.vectors["model"]["modelSha256"])
        self.assertEqual(proof["labels"]["sha256"], self.vectors["model"]["labelsSha256"])
        self.assertEqual(proof["labels"]["classes"], self.vectors["model"]["classes"])
        self.assertFalse(proof["realChallengeInference"]["currentAcceptance"])
        self.assertFalse(proof["liveAcceptance"]["currentAcceptance"])
        serialized = json.dumps(proof, ensure_ascii=False)
        self.assertNotIn("C:\\", serialized)
        self.assertNotIn("D:\\", serialized)

    def test_offline_proof_binds_current_entry_and_test(self) -> None:
        entry_sha = hashlib.sha256((CASE_ROOT / "entry.py").read_bytes()).hexdigest()
        test_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.assertEqual(self.vectors["entrySha256"], entry_sha)
        self.assertEqual(self.vectors["testArtifactSha256"], test_sha)

    def test_indices_to_userresponse(self) -> None:
        vector = self.vectors["indices"]
        self.assertEqual(
            entry.indices_to_userresponse(vector["input"], vector["count"]),
            vector["expected"],
        )

    def test_indices_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            entry.indices_to_userresponse([1, 1, 2], 3)

    def test_lot_rule_is_inclusive(self) -> None:
        vector = self.vectors["lot"]
        self.assertEqual(
            entry.resolve_lot_fields(vector["lotNumber"], vector["rules"]),
            vector["expected"],
        )

    def test_decode_uri_preserves_reserved_escape(self) -> None:
        vector = self.vectors["decodeUri"]
        self.assertEqual(
            entry.decode_uri_bytes(vector["input"]).decode("ascii"),
            vector["expectedAscii"],
        )

    def test_djb2_vector(self) -> None:
        vector = self.vectors["djb2"]
        self.assertEqual(entry.djb2_5381(vector["input"]), vector["expected"])

    def test_gct_biht_vector(self) -> None:
        vector = self.vectors["gct"]
        self.assertEqual(entry.calculate_biht(vector["source"]), vector["expectedBiht"])

    def test_aes_ascii_zero_iv_vector(self) -> None:
        vector = self.vectors["aes"]
        ciphertext, _ = entry.encrypt_aes(
            vector["payload"], vector["keyAscii"].encode("ascii")
        )
        self.assertEqual(ciphertext, vector["expectedCiphertextHex"])

    def test_pow_vector(self) -> None:
        vector = self.vectors["pow"]
        self.assertTrue(
            entry.verify_pow_message(vector["message"], vector["digest"], vector["bits"])
        )
        self.assertEqual(
            hashlib.sha256(vector["message"].encode("utf-8")).hexdigest(),
            vector["digest"],
        )

    def test_pow_is_difficulty_checked_and_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 255"):
            entry.verify_pow_message("message", "0" * 64, 0)
        detail = {
            "version": "1",
            "bits": 255,
            "hashfunc": "sha256",
            "datetime": "2026-07-31T00:00:00Z",
        }
        with self.assertRaisesRegex(TimeoutError, "within 2 attempts"):
            entry.solve_pow(
                "captcha",
                "lot",
                detail,
                nonce_factory=lambda: "fixed",
                max_attempts=2,
            )

    def test_checkpoint_execution_requires_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(PermissionError, "explicit per-run approval"):
                entry._load_model(Path(tmp))

    def test_runtime_cache_defers_settings_to_installed_ultralytics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = entry.configure_runtime_cache(Path(tmp))
            self.assertTrue((runtime / "datasets").is_dir())
            self.assertFalse(
                (runtime / "ultralytics" / "Ultralytics" / "settings.json").exists()
            )

    def test_ultralytics_settings_are_project_pinned_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "js_reverse_cache" / "_runtime"
            fake_settings = {
                "datasets_dir": "old-datasets",
                "weights_dir": "old-weights",
                "runs_dir": "old-runs",
                "sync": True,
                "hub": True,
                "clearml": True,
                "comet": True,
                "dvc": True,
                "mlflow": True,
                "neptune": True,
                "raytune": True,
                "tensorboard": True,
                "wandb": True,
                "vscode_msg": True,
                "openvino_msg": True,
            }
            entry.apply_ultralytics_runtime_settings(fake_settings, runtime)
            self.assertEqual(fake_settings["datasets_dir"], str(runtime / "datasets"))
            self.assertEqual(fake_settings["weights_dir"], str(runtime / "weights"))
            self.assertEqual(fake_settings["runs_dir"], str(runtime / "runs"))
            self.assertFalse(any(value is True for value in fake_settings.values()))

    def test_installed_model_pack_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            installed = entry.install_model_pack(project_root)
            selected = entry.select_model_pack(project_root)
            self.assertEqual(selected, project_root / "models" / entry.MODEL_PACK_NAME)
            self.assertEqual(Path(installed["model"]).parent, selected)
            self.assertEqual(entry.verify_model_assets(selected), self.vectors["model"])
            Path(installed["labels"]).unlink()
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                entry.select_model_pack(project_root)

    def test_model_class_map_must_match_labels(self) -> None:
        class FakeModel:
            names = {0: "alpha", 1: "beta"}

        entry.validate_model_class_names(FakeModel(), ["alpha", "beta"])
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            entry.validate_model_class_names(FakeModel(), ["beta", "alpha"])

    @staticmethod
    def tile(index: int, top1: str, target_score: float = 0.01) -> dict:
        probabilities = {top1: 0.9}
        if top1 != "wanted":
            probabilities["wanted"] = target_score
        return {
            "index": index,
            "top1": top1,
            "top1Confidence": probabilities[top1],
            "probabilities": probabilities,
        }

    def test_recognition_uses_unique_three_tile_consensus(self) -> None:
        labels = ["cat", "u0", "u1", "u2", "u3", "cat", "cat", "u4", "u5"]
        tiles = [self.tile(index, label) for index, label in enumerate(labels)]
        actual = entry.select_nine_grid_tiles({"cat": 0.01}, "u0", tiles, 3)
        self.assertEqual(actual["indices"], [0, 5, 6])
        self.assertEqual(actual["strategy"], "tile-consensus")

    def test_recognition_uses_question_to_break_exact_group_tie(self) -> None:
        labels = ["cat", "cat", "cat", "dog", "dog", "dog", "u0", "u1", "u2"]
        tiles = [self.tile(index, label) for index, label in enumerate(labels)]
        actual = entry.select_nine_grid_tiles(
            {"cat": 0.2, "dog": 0.8}, "dog", tiles, 3
        )
        self.assertEqual(actual["indices"], [3, 4, 5])
        self.assertEqual(actual["strategy"], "tile-consensus-question-tiebreak")

    def test_recognition_rejects_unresolved_exact_group_tie(self) -> None:
        labels = ["cat", "cat", "cat", "dog", "dog", "dog", "u0", "u1", "u2"]
        tiles = [self.tile(index, label) for index, label in enumerate(labels)]
        with self.assertRaisesRegex(RuntimeError, "cannot disambiguate"):
            entry.select_nine_grid_tiles(
                {"cat": 0.5, "dog": 0.5}, "dog", tiles, 3
            )

    def test_recognition_ranks_question_target_confidence(self) -> None:
        tiles = [
            self.tile(index, f"u{index}", target_score=(index + 1) / 100)
            for index in range(9)
        ]
        actual = entry.select_nine_grid_tiles({"wanted": 0.9}, "wanted", tiles, 3)
        self.assertEqual(actual["indices"], [6, 7, 8])
        self.assertEqual(actual["strategy"], "question-target-confidence")

    def test_recognition_uses_largest_group_only_with_three_candidates(self) -> None:
        labels = ["cat", "cat", "cat", "cat", "u0", "u1", "u2", "u3", "u4"]
        tiles = [self.tile(index, label) for index, label in enumerate(labels)]
        for index, tile in enumerate(tiles[:4]):
            tile["top1Confidence"] = 0.5 + index / 10
            tile["probabilities"]["cat"] = tile["top1Confidence"]
        actual = entry.select_nine_grid_tiles({"wanted": 0.9}, "wanted", tiles, 3)
        self.assertEqual(actual["indices"], [1, 2, 3])
        self.assertEqual(actual["strategy"], "largest-tile-group-fallback")

    def test_recognition_rejects_ambiguous_largest_groups(self) -> None:
        labels = ["cat", "cat", "cat", "cat", "dog", "dog", "dog", "dog", "u0"]
        tiles = [self.tile(index, label) for index, label in enumerate(labels)]
        with self.assertRaisesRegex(RuntimeError, "largest tile group is ambiguous"):
            entry.select_nine_grid_tiles({"wanted": 0.9}, "wanted", tiles, 3)

    def test_recognize_cache_runs_with_injected_predictions(self) -> None:
        labels = ["cat", "u0", "u1", "u2", "u3", "cat", "cat", "u4", "u5"]
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            cache = project_root / "js_reverse_cache" / "round-1"
            cache.mkdir(parents=True)
            (cache / "manifest.json").write_text(
                json.dumps({"image_meta": {"count": 3}}),
                encoding="utf-8",
            )
            (cache / "ques_0.png").write_bytes(b"fixture")
            for index in range(9):
                (cache / f"tile_{index}.jpg").write_bytes(b"fixture")

            loader_calls = []

            def loader(root: Path, allowed: bool) -> tuple:
                loader_calls.append((root, allowed))
                return object(), sorted(set(labels))

            def classifier(_model: object, path: Path, _labels: list) -> tuple:
                if path.name.startswith("ques_"):
                    return {"cat": 0.8}, "cat"
                index = int(path.stem.split("_")[1])
                label = labels[index]
                return {label: 0.9}, label

            actual = entry.recognize_cache(
                cache,
                project_root,
                model_loader=loader,
                classifier=classifier,
            )
            self.assertEqual(actual["indices"], [0, 5, 6])
            self.assertTrue((cache / "recognize.json").is_file())
            self.assertEqual(loader_calls, [(project_root, False)])

    def test_recognition_cache_must_stay_under_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "js_reverse_cache"):
                entry.recognize_cache(root / "outside", root / "project")

    def test_invalid_round_never_reaches_model_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            cache = project_root / "js_reverse_cache" / "round-invalid"
            cache.mkdir(parents=True)
            (cache / "manifest.json").write_text(
                json.dumps({"image_meta": {"count": 4}}),
                encoding="utf-8",
            )

            def forbidden_loader(_root: Path, _allowed: bool) -> tuple:
                self.fail("model loader must not run for an invalid round")

            with self.assertRaisesRegex(ValueError, "nine_nums=3"):
                entry.recognize_cache(cache, project_root, model_loader=forbidden_loader)

            (cache / "manifest.json").write_text(
                json.dumps({"image_meta": {"count": 3}}),
                encoding="utf-8",
            )
            (cache / "ques_0.png").write_bytes(b"fixture")
            with self.assertRaisesRegex(FileNotFoundError, "tile files missing"):
                entry.recognize_cache(cache, project_root, model_loader=forbidden_loader)

    def test_offline_scope_marker(self) -> None:
        self.assertEqual(self.vectors["activeScope"], "offline-only")
        self.assertTrue(self.vectors["passed"])


if __name__ == "__main__":
    unittest.main()
