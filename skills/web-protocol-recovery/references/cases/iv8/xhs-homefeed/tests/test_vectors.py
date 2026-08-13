import hashlib
import json
import sys
import unittest
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR))

from entry import canonical_md5, load_runtime, run, vector_shape


class XhsVectorTests(unittest.TestCase):
    def test_vectors_are_redacted_and_parseable(self):
        vectors = json.loads((CASE_DIR / "fixtures" / "vectors.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(vectors["vectors"]), 3)
        serialized = json.dumps(vectors)
        for secret in ("web_session", "a1", "b1", "sec_poison_id"):
            self.assertNotIn(secret + "\":\"", serialized)

    def test_canonical_hash_vector(self):
        u, p = canonical_md5("/api/sns/web/v2/user/me")
        self.assertEqual(u, "e66aa8f9e80c2f74fda53620925c6723")
        self.assertEqual(p, u)

    def test_runtime_is_frozen_and_shape_is_local(self):
        runtime = load_runtime()
        self.assertGreater(len(runtime), 100000)
        self.assertNotIn("web_session", runtime)
        shape = vector_shape("/api/sns/web/v2/user/me")
        self.assertEqual(shape["x3_prefix"], "mns")
        self.assertGreaterEqual(shape["x3_min_length"], 32)
        result = run()
        self.assertEqual(result["status"], "offline")
        self.assertEqual(result["vector_count"], 3)
        self.assertEqual(result["runtime_sha256"], hashlib.sha256(runtime.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
