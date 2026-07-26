from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


CASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_ROOT))

import entry


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


if __name__ == "__main__":
    unittest.main()
