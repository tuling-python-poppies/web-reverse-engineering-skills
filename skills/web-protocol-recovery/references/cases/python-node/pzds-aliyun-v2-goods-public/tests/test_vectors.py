from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import cast


CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry
import pull_live_state


class PzdsAliyunV2Vectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads((CASE_ROOT / "fixtures" / "vectors.json").read_text(encoding="utf-8"))

    def test_goods_body_sha256(self) -> None:
        body = entry.build_goods_page_body()
        self.assertEqual(hashlib.sha256(body).hexdigest(), self.vectors["request"]["bodySha256"])

    def test_field21_vectors(self) -> None:
        for item in self.vectors["field21"]:
            if "xorMaskAscii" in item:
                mask = item["xorMaskAscii"].encode("ascii")
            else:
                mask = bytes.fromhex(item["xorMaskHex"])
            self.assertEqual(entry.build_field21(item["suffix"], item["sourceKey"], mask), item["expected"])

    def test_rpc_signature(self) -> None:
        sample = self.vectors["rpcSignature"]
        self.assertEqual(entry.sign_rpc(sample["params"], sample["secret"], sample["method"]), sample["expected"])

    def test_device_token_roundtrip(self) -> None:
        session_id = "0123456789abcdef0123456789abcdef-abcd-ef01"
        key = "0123456789abcdef"
        fields = [""] * 133
        fields[0] = "W.10051"
        fields[21] = "WStYKVldLlw="
        plaintext = "#".join(fields)
        token = entry.build_device_token(session_id, plaintext, 123, key)
        parsed = entry.parse_device_token(token)
        self.assertEqual(parsed.session_id, session_id)
        self.assertEqual(parsed.counter, 123)
        self.assertEqual(parsed.checksum, entry.device_token_checksum(parsed.platform, parsed.session_id, parsed.payload, parsed.counter))
        self.assertEqual(entry.decrypt_device_payload(parsed, key), plaintext)

    def test_data_builder_asset(self) -> None:
        sample = self.vectors["dataBuilder"]
        process = subprocess.run(
            ["node", str(CASE_ROOT / "assets" / "data_builder.js")],
            input=json.dumps({"input": sample["input"], "key": sample["key"]}),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(process.stdout)["output"], sample["expected"])

    def _device_config_fixture(self) -> entry.DeviceConfig:
        return entry.DeviceConfig(**self.vectors["deviceConfig"]["parsed"])

    def test_device_config_roundtrip(self) -> None:
        sample = self.vectors["deviceConfig"]
        config = self._device_config_fixture()
        self.assertEqual(entry.build_device_config_blob(config), sample["blob"])
        parsed = entry.parse_device_config(sample["blob"])
        self.assertEqual(
            {key: getattr(parsed, key) for key in sample["parsed"]},
            sample["parsed"],
        )

    def test_log_envelope_vectors(self) -> None:
        sample = self.vectors["logEnvelope"]
        config = self._device_config_fixture()
        platform = sample["devicePlatform"]
        full_fields = ["#"] * 36 + [platform] + ["#"] * (142 - 37)
        full_fields[21] = "WStYKVldLlw="
        log2 = entry.build_log2_data(
            config,
            sample["scene"],
            full_fields,
            gather_cost_ms=sample["gatherCostLog2"],
            timestamp_ms=1785065901234,
            device_platform=platform,
        )
        self.assertEqual(log2, sample["log2"])
        combat_504 = {
            "mousemove": [{"x": 1, "y": 2, "t": 1000}],
            "mouseclick": [],
            "keyup": [],
            "scrollTop": 0,
            "scrollLeft": 0,
            "clientType": "desktop",
            "startTime": 1785065900000,
            "timestamp": "1785065900",
        }
        log3 = entry.build_log3_data(
            config,
            sample["scene"],
            "511-status-payload",
            combat_504,
            gather_cost_ms=sample["gatherCostLog3"],
            timestamp_ms=1785065902467,
            device_platform=platform,
        )
        self.assertEqual(log3, sample["log3"])

    def test_verify_params_vector(self) -> None:
        sample = self.vectors["verifyParams"]
        params = entry.make_verify_params(
            scene_id="19x5u7lo",
            certify_id="0a0611221785065901234567e6043",
            device_token="TOKEN-REDACTED",
            data="DATA-REDACTED",
            user_user_id="UUUU-TEMPLATE",
            access_key_id="TESTKEY",
            signature_nonce="nonce-verify",
            secret=sample["secret"],
        )
        self.assertEqual(params, sample["params"])

    def test_build_data_vector(self) -> None:
        sample = self.vectors["dataBuilderTrack"]
        track_state = {
            "TrackList": {
                "mc": "1", "tc": "2", "mu": "3", "te": "4", "mp": "5",
                "tmv": "6", "mm": "7", "ks": "8", "fi": "9",
                "startTime": 1000, "si": "10",
            },
            "TrackStartTime": 1000,
            "VerifyTime": 2000,
            "arg": "arg11",
        }
        built = entry.build_data(track_state, nonce=sample["nonce"])
        self.assertEqual(built["data"], sample["data"])
        self.assertEqual(built["compressed"], sample["compressed"])
        self.assertEqual(built["trackJson"], sample["trackJson"])

    def test_build_arg_vector(self) -> None:
        sample = self.vectors["buildArg"]
        built = entry.build_arg("0a0611221785065901234567e6043", key=sample["key"])
        self.assertEqual(built["arg"], sample["arg"])

    def test_track_template_shape(self) -> None:
        template = json.loads(
            (CASE_ROOT / "fixtures" / "track-template.json").read_text(encoding="utf-8")
        )
        self.assertEqual(template["acceptance"]["liveUse"], "not-standalone")
        self.assertEqual(
            template["acceptance"]["projectSeedPath"],
            "js_reverse_cache/private/pzds/track_seed.json",
        )
        track = template["track"]
        track_list = track["TrackList"]
        for key in ("mc", "tc", "mu", "te", "mp", "tmv", "mm", "ks", "fi", "startTime", "si"):
            self.assertIn(key, track_list)
        for key in ("TrackStartTime", "VerifyTime", "arg"):
            self.assertIn(key, track)
        generation = template["generation"]
        self.assertIn("timestampFields", generation)
        self.assertEqual(
            generation["screenInfo"]["parts"],
            len(track_list["si"].split(",")),
        )
        for field in generation["timestampFields"]:
            self.assertIn(field, track_list)

    def test_wasm_sign_asset(self) -> None:
        sample = self.vectors["pzdsWasmSign"]
        signed = entry.pzds_wasm_sign(
            entry.build_goods_page_body(),
            method=sample["method"],
            timestamp=sample["timestamp"],
            random_value=sample["random"],
        )
        self.assertEqual(signed["Sign"], sample["expectedSign"])
        self.assertEqual(signed["PZTimestamp"], sample["timestamp"])
        self.assertEqual(signed["Random"], sample["random"])

    def test_challenge_parser(self) -> None:
        payload = {
            "sceneId": "19x5u7lo",
            "traceid": "0a099c-redacted",
            "token": "redacted-token",
            "userId": "redacted-user",
            "userUserId": "redacted-user-user",
            "type": "POST",
        }
        html = "<textarea id=renderData>var requestInfo = " + json.dumps(payload, separators=(",", ":")) + ";</textarea>"
        self.assertEqual(entry.parse_challenge_html(html)["sceneId"], "19x5u7lo")

    def test_offline_proof_binds_current_entry_and_test(self) -> None:
        proof = json.loads(
            (CASE_ROOT / "fixtures" / "offline-proof.summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            proof["caseId"], "python-node-pzds-aliyun-v2-goods-public"
        )
        self.assertEqual(proof["activeScope"], "offline-only")
        self.assertTrue(proof["passed"])
        self.assertFalse(proof["historicalLiveProofIsCurrentAcceptance"])
        self.assertEqual(
            proof["entrySha256"],
            hashlib.sha256((CASE_ROOT / "entry.py").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            proof["testArtifactSha256"],
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )

    def test_live_state_requires_explicit_raw_secret_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "js_reverse_cache" / "private" / "pzds"
            state_root.mkdir(parents=True)
            (state_root / "session.json").write_text(
                json.dumps({"token": "test-token", "pzId": "pz"}),
                encoding="utf-8",
            )
            with self.assertRaises(PermissionError):
                pull_live_state.load_session(root)
            with self.assertRaises(PermissionError):
                pull_live_state.load_session(
                    root, raw_secret_handling_confirmed=cast(bool, "false")
                )
            session = pull_live_state.load_session(
                root, raw_secret_handling_confirmed=True
            )
            self.assertEqual(session["sessionPath"], "js_reverse_cache/private/pzds/session.json")
            inspection = pull_live_state.inspect_project(root)
            self.assertEqual(inspection["missing"], ["rawSecretHandling"])

    def test_live_profile_uses_canonical_private_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "js_reverse_cache" / "private" / "pzds"
            state_root.mkdir(parents=True)
            profile = {
                "feilinVersion": "feilin-test",
                "userAgent": "test-agent",
                "fullDeviceFields": [""] * 111,
                "tokenFields": [""] * 111,
                "field21": {"sourceKey": "test", "xorMaskHex": "00"},
                "combat511": {},
                "combat504": {},
            }
            (state_root / "t001_profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            loaded = pull_live_state.load_profile(
                root, raw_secret_handling_confirmed=True
            )
            self.assertEqual(
                loaded["profilePath"],
                "js_reverse_cache/private/pzds/t001_profile.json",
            )
            self.assertEqual(loaded["fullDeviceFieldCount"], 111)
            self.assertEqual(loaded["tokenFieldCount"], 111)
            self.assertTrue(loaded["hasField21"])
            self.assertNotIn("field21", loaded)

    def test_live_state_rejects_non_string_protocol_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "js_reverse_cache" / "private" / "pzds"
            state_root.mkdir(parents=True)
            bad_profile = {
                "feilinVersion": "feilin-test",
                "userAgent": "test-agent",
                "fullDeviceFields": "x" * 133,
                "tokenFields": [""] * 133,
                "field21": {},
                "combat511": {},
                "combat504": {},
            }
            (state_root / "t001_profile.json").write_text(
                json.dumps(bad_profile), encoding="utf-8"
            )
            (state_root / "session.json").write_text(
                json.dumps({"token": 123}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "fullDeviceFields"):
                pull_live_state.load_profile(root, raw_secret_handling_confirmed=True)
            with self.assertRaisesRegex(ValueError, "session missing keys"):
                pull_live_state.load_session(root, raw_secret_handling_confirmed=True)
            bad_profile["fullDeviceFields"] = [""] * 111
            bad_profile["tokenFields"] = [""] * 142
            (state_root / "t001_profile.json").write_text(
                json.dumps(bad_profile), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "length must match"):
                pull_live_state.load_profile(root, raw_secret_handling_confirmed=True)
            bad_profile["tokenFields"] = [""] * 111
            bad_profile["userAgent"] = 123
            bad_profile["field21"] = {"sourceKey": "test", "xorMaskHex": "00"}
            (state_root / "t001_profile.json").write_text(
                json.dumps(bad_profile), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "userAgent"):
                pull_live_state.load_profile(root, raw_secret_handling_confirmed=True)

    def test_live_state_rejects_reparse_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "js_reverse_cache" / "private" / "pzds"
            state_root.mkdir(parents=True)
            session_path = state_root / "session.json"
            session_path.write_text(json.dumps({"token": "test-token"}), encoding="utf-8")
            with mock.patch.object(
                pull_live_state,
                "_is_reparse_point",
                side_effect=lambda path: path == session_path,
            ):
                with self.assertRaisesRegex(ValueError, "reparse path"):
                    pull_live_state.load_session(root, raw_secret_handling_confirmed=True)

    def test_process_keeps_private_state_behind_raw_secret_gate(self) -> None:
        process = (CASE_ROOT / "PROCESS.md").read_text(encoding="utf-8")
        self.assertIn("raw-secret-handling", process)
        self.assertIn("js_reverse_cache/private/pzds/session.json", process)
        self.assertIn("js_reverse_cache/private/pzds/t001_profile.json", process)
        self.assertIn("utils/t001_profile_refresh.py", process)
        self.assertIn("websocket-client", process)
        self.assertIn("ordinary Chrome", process)
        self.assertIn("CloakBrowser", process)
        self.assertIn("js_reverse_cache/private/pzds/track_seed.json", process)
        self.assertIn("seed-derived track", process)
        self.assertIn("structural template alone", process)
        self.assertIn("111", process)
        self.assertIn("133", process)
        self.assertIn("142", process)
        self.assertNotIn("verifier/t001_profile.json", process)
        self.assertNotIn("js_reverse_cache/" + "pzds_session.json", process)
        self.assertNotIn("update_" + "t001_profile.py", process)
        self.assertIn("raw CDP", process)


if __name__ == "__main__":
    unittest.main()
