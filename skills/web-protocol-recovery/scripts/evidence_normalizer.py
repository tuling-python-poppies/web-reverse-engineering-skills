#!/usr/bin/env python3
"""Normalize HAR or transcript JSON into a secret-free ordered proof package."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlsplit

from providers.path_safety import PlainPathGuard, absolute_no_resolve


SCHEMA = "web-protocol-recovery-evidence/v1"
MAX_INPUT_BYTES = 20 * 1024 * 1024
SENSITIVE_NAME = re.compile(
    r"(?i)(authorization|cookie|token|secret|password|passwd|session|csrf|api[-_]?key|credential)"
)
TOKEN_LIKE = re.compile(r"^[A-Za-z0-9_./+=:-]{20,}$")
SAFE_HEADER_NAMES = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "content-length",
    "content-type",
}
VARIABLE_PATH_SEGMENT = re.compile(
    r"(?i)^(?:\d{2,}|[0-9a-f]{8}(?:-[0-9a-f-]{27,})?|[^@/]+@[^@/]+|[A-Za-z0-9_.+=-]{20,})$"
)


class EvidenceError(ValueError):
    pass


class Redactor:
    def __init__(self, key: bytes) -> None:
        if len(key) < 16:
            raise EvidenceError("HMAC key must be at least 16 bytes")
        self.key = key

    def value(self, raw: Any) -> Dict[str, Any]:
        data = canonical_bytes(raw)
        return {
            "redacted": True,
            "length": len(data),
            "hmacSha256": hmac.new(self.key, data, hashlib.sha256).hexdigest(),
        }


def canonical_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sensitive(name: Any, value: Any) -> bool:
    name_text = str(name or "")
    value_text = value if isinstance(value, str) else ""
    return bool(SENSITIVE_NAME.search(name_text) or TOKEN_LIKE.fullmatch(value_text))


def safe_scalar(name: Any, value: Any, redactor: Redactor) -> Any:
    if sensitive(name, value):
        return redactor.value(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > 256:
        return {"length": len(text.encode("utf-8")), "sha256": sha256_bytes(text.encode("utf-8"))}
    return text


def iter_headers(headers: Any, label: str) -> Iterable[Tuple[str, str]]:
    if headers is None:
        return []
    if isinstance(headers, Mapping):
        return [(str(k), str(v)) for k, v in headers.items()]
    if isinstance(headers, list):
        rows: List[Tuple[str, str]] = []
        for index, item in enumerate(headers):
            if isinstance(item, Mapping) and "name" in item:
                rows.append((str(item["name"]), str(item.get("value", ""))))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                rows.append((str(item[0]), str(item[1])))
            else:
                raise EvidenceError(f"{label}[{index}] is not a header pair")
        return rows
    raise EvidenceError(f"{label} must be a mapping or ordered list")


def normalize_headers(headers: Any, redactor: Redactor, label: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for index, (name, value) in enumerate(iter_headers(headers, label)):
        normalized_name = name.lower()
        normalized_value = (
            safe_scalar(name, value, redactor)
            if normalized_name in SAFE_HEADER_NAMES and not sensitive(name, value)
            else redactor.value(value)
        )
        result.append({"index": index, "name": normalized_name, "value": normalized_value})
    return result


def body_bytes(value: Any, encoding: Optional[str] = None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, (dict, list)):
        return canonical_bytes(value)
    text = str(value)
    if encoding == "base64":
        try:
            return base64.b64decode(text, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise EvidenceError("invalid base64 body") from exc
    return text.encode("utf-8")


def body_descriptor(value: Any, encoding: Optional[str] = None) -> Dict[str, Any]:
    data = body_bytes(value, encoding)
    return {"length": len(data), "sha256": sha256_bytes(data)}


def normalize_url(url: Any, redactor: Redactor) -> Dict[str, Any]:
    parsed = urlsplit(str(url or ""))
    query: List[Dict[str, Any]] = []
    for index, (name, value) in enumerate(parse_qsl(parsed.query, keep_blank_values=True)):
        query.append({"index": index, "name": name, "value": redactor.value(value)})
    authority = parsed.hostname or ""
    if parsed.port:
        authority = f"{authority}:{parsed.port}"
    return {
        "scheme": parsed.scheme.lower(),
        "authority": authority.lower(),
        "pathSegments": [
            redactor.value(segment) if VARIABLE_PATH_SEGMENT.fullmatch(segment) else segment
            for segment in parsed.path.split("/")
        ],
        "query": query,
        "fragmentPresent": bool(parsed.fragment),
    }


def normalize_state_writes(value: Any, redactor: Redactor) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvidenceError("stateWrites must be a list")
    result: List[Dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise EvidenceError(f"stateWrites[{index}] must be an object")
        name = str(item.get("name", item.get("key", "unknown")))
        result.append({
            "index": index,
            "surface": str(item.get("surface", "unknown")),
            "name": name,
            "value": redactor.value(item.get("value", "")),
        })
    return result


def har_body(message: Mapping[str, Any], request: bool) -> Dict[str, Any]:
    if request:
        post = message.get("postData")
        if isinstance(post, Mapping):
            return body_descriptor(post.get("text", ""), post.get("encoding"))
        return body_descriptor(b"")
    content = message.get("content")
    if isinstance(content, Mapping):
        return body_descriptor(content.get("text", ""), content.get("encoding"))
    return body_descriptor(b"")


def normalize_har(document: Mapping[str, Any], redactor: Redactor) -> List[Dict[str, Any]]:
    log = document.get("log")
    entries = log.get("entries") if isinstance(log, Mapping) else None
    if not isinstance(entries, list):
        raise EvidenceError("HAR log.entries must be a list")
    steps: List[Dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise EvidenceError(f"HAR entry {index} must be an object")
        request = entry.get("request", {})
        response = entry.get("response", {})
        if not isinstance(request, Mapping) or not isinstance(response, Mapping):
            raise EvidenceError(f"HAR entry {index} request/response must be objects")
        steps.append({
            "index": index,
            "request": {
                "method": str(request.get("method", "GET")).upper(),
                "url": normalize_url(request.get("url", ""), redactor),
                "headers": normalize_headers(request.get("headers"), redactor, f"entry[{index}].request.headers"),
                "body": har_body(request, True),
            },
            "response": {
                "status": int(response.get("status", 0) or 0),
                "headers": normalize_headers(response.get("headers"), redactor, f"entry[{index}].response.headers"),
                "body": har_body(response, False),
                "redirect": normalize_url(response.get("redirectURL", ""), redactor) if response.get("redirectURL") else None,
            },
            "stateWrites": [],
        })
    return steps


def normalize_transcript(document: Mapping[str, Any], redactor: Redactor) -> List[Dict[str, Any]]:
    steps = document.get("steps")
    if not isinstance(steps, list):
        raise EvidenceError("transcript steps must be a list")
    result: List[Dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise EvidenceError(f"step {index} must be an object")
        request = step.get("request", {})
        response = step.get("response", {})
        if not isinstance(request, Mapping) or not isinstance(response, Mapping):
            raise EvidenceError(f"step {index} request/response must be objects")
        req_body = request.get("body", b"")
        res_body = response.get("body", b"")
        result.append({
            "index": index,
            "request": {
                "method": str(request.get("method", "GET")).upper(),
                "url": normalize_url(request.get("url", ""), redactor),
                "headers": normalize_headers(request.get("headers"), redactor, f"step[{index}].request.headers"),
                "body": body_descriptor(req_body, request.get("bodyEncoding")),
            },
            "response": {
                "status": int(response.get("status", 0) or 0),
                "headers": normalize_headers(response.get("headers"), redactor, f"step[{index}].response.headers"),
                "body": body_descriptor(res_body, response.get("bodyEncoding")),
                "redirect": normalize_url(response["redirect"], redactor) if response.get("redirect") else None,
            },
            "stateWrites": normalize_state_writes(step.get("stateWrites"), redactor),
        })
    return result


def normalize_document(document: Any, key: bytes) -> Dict[str, Any]:
    if not isinstance(document, Mapping):
        raise EvidenceError("input JSON must be an object")
    redactor = Redactor(key)
    if isinstance(document.get("log"), Mapping):
        source_format = "har"
        steps = normalize_har(document, redactor)
    elif isinstance(document.get("steps"), list):
        source_format = "transcript"
        steps = normalize_transcript(document, redactor)
    else:
        raise EvidenceError("input is neither HAR nor transcript JSON")
    source_hash = sha256_bytes(canonical_bytes(document))
    return {
        "schemaVersion": SCHEMA,
        "source": {"format": source_format, "sha256": source_hash},
        "chains": [{"id": "chain-0", "steps": steps}],
    }


def contained_path(project_root: Path, path: Path) -> Path:
    root = absolute_no_resolve(project_root)
    candidate = absolute_no_resolve(path)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise EvidenceError(f"path escapes project root: {candidate}") from exc
    return candidate


def load_json(path: Path, project_root: Path) -> Any:
    path = contained_path(project_root, path)
    with PlainPathGuard() as guard:
        guard.lock_directory(project_root)
        guard.lock_file(path)
        data = guard.read_bytes(path)
    if len(data) > MAX_INPUT_BYTES:
        raise EvidenceError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
    return json.loads(data.decode("utf-8-sig"))


def read_key(args: argparse.Namespace) -> bytes:
    if args.hmac_key_env:
        value = os.environ.get(args.hmac_key_env)
        if value is None:
            raise EvidenceError(f"environment variable is not set: {args.hmac_key_env}")
        return value.encode("utf-8")
    if args.hmac_key_file:
        return Path(args.hmac_key_file).read_bytes().strip()
    raise EvidenceError("provide --hmac-key-env or --hmac-key-file")


def write_new(path: Path, document: Mapping[str, Any], project_root: Path) -> None:
    path = contained_path(project_root, path)
    if not path.parent.is_dir():
        raise EvidenceError(f"output parent must already exist: {path.parent}")
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with PlainPathGuard() as guard:
        guard.lock_directory(project_root)
        guard.lock_directory(path.parent)
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())


def run_self_test() -> None:
    sample = {
        "steps": [{
            "request": {
                "method": "post",
                "url": "https://example.test/api?a=1&token=secret-value-1234567890",
                "headers": [["X-Order", "a"], ["X-Order", "b"], ["Cookie", "sid=secret"]],
                "body": "x=1",
            },
            "response": {"status": 200, "headers": [["Set-Cookie", "sid=next"]], "body": "ok"},
            "stateWrites": [{"surface": "cookie", "name": "sid", "value": "next"}],
        }]
    }
    result = normalize_document(sample, b"0123456789abcdef0123456789abcdef")
    step = result["chains"][0]["steps"][0]
    assert [item["name"] for item in step["request"]["headers"]] == ["x-order", "x-order", "cookie"]
    assert step["request"]["headers"][0]["value"]["redacted"] is True
    assert step["request"]["headers"][2]["value"]["redacted"] is True
    assert step["request"]["url"]["query"][0]["value"]["redacted"] is True
    rendered = json.dumps(result, sort_keys=True)
    assert "secret-value" not in rendered and "sid=secret" not in rendered
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.json"
        output_path = root / "output.json"
        # newline="\n" everywhere a script writes text, without exception. This
        # particular file is scratch input for the self-test and would survive a
        # CRLF translation, but the same call in build_case_registry.py silently
        # broke every case hash on non-Windows checkouts. The rule is cheaper to
        # keep than to reason about case by case.
        input_path.write_text(json.dumps(sample), encoding="utf-8", newline="\n")
        loaded = load_json(input_path, root)
        write_new(output_path, normalize_document(loaded, b"0123456789abcdef0123456789abcdef"), root)
        assert output_path.is_file()
        try:
            contained_path(root, root.parent / "outside.json")
        except EvidenceError:
            pass
        else:
            raise AssertionError("project-root containment did not fail closed")
    print("evidence_normalizer_self_test=PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--project-root")
    key = parser.add_mutually_exclusive_group()
    key.add_argument("--hmac-key-env")
    key.add_argument("--hmac-key-file")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            run_self_test()
            return 0
        if not args.input or not args.output or not args.project_root:
            raise EvidenceError("input, output, and --project-root are required")
        project_root = absolute_no_resolve(Path(args.project_root))
        document = normalize_document(load_json(Path(args.input), project_root), read_key(args))
        write_new(Path(args.output), document, project_root)
        print(f"normalized_steps={len(document['chains'][0]['steps'])}")
        return 0
    except (EvidenceError, OSError, json.JSONDecodeError, AssertionError) as exc:
        print(f"evidence_normalizer=FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
