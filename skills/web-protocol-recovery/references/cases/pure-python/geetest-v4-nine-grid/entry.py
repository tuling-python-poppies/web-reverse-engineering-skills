#!/usr/bin/env python3
"""Offline Geetest GT4 nine-grid protocol and model helpers.

This case entry performs no network traffic and creates no files on import.
Live /load and /verify egress belongs to a gated Python collector. The bundled
model can be loaded directly from this case or explicitly installed into a
project for offline reuse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad


CASE_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = CASE_ROOT / "assets"
MODEL_PATH = ASSETS_ROOT / "geetest_nine_model.pt"
LABELS_PATH = ASSETS_ROOT / "labels.txt"
MODEL_MANIFEST_PATH = ASSETS_ROOT / "MODEL.json"

AES_IV = b"0000000000000000"
RSA_N_HEX = (
    "c1e3934d1614465b33053e7f48ee4ec87b14b95ef88947713d25eecbff7e74c"
    "7977d02dc1d9451f79dd5d1c10c29acb6a9b4d6fb7d0a0279b6719e1772565f"
    "09af627715919221aef91899cae08c0d686d748b20a3603be2318ca6bc2b597"
    "06592a9219d0bf05c9f65023a21d2330807252ae0066d59ceefa5f2748ea80bab81"
)
RSA_E = 65537
NEED = 3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model_manifest() -> Dict[str, Any]:
    return json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))


def load_labels(path: Path = LABELS_PATH) -> List[str]:
    labels = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [label for label in labels if label and not label.startswith("#")]


def verify_model_assets() -> Dict[str, Any]:
    manifest = load_model_manifest()
    expected_model = manifest["model"]
    expected_labels = manifest["labels"]
    actual_model_sha = sha256_file(MODEL_PATH)
    actual_labels_sha = sha256_file(LABELS_PATH)
    actual_bytes = MODEL_PATH.stat().st_size
    labels = load_labels()

    if actual_model_sha != expected_model["sha256"]:
        raise RuntimeError("model SHA-256 mismatch")
    if actual_bytes != expected_model["bytes"]:
        raise RuntimeError("model byte-size mismatch")
    if actual_labels_sha != expected_labels["sha256"]:
        raise RuntimeError("labels SHA-256 mismatch")
    if len(labels) != manifest["classes"]:
        raise RuntimeError("label count mismatch")

    return {
        "modelId": manifest["modelId"],
        "modelSha256": actual_model_sha,
        "modelBytes": actual_bytes,
        "labelsSha256": actual_labels_sha,
        "classes": len(labels),
    }


def configure_runtime_cache(project_root: Path) -> Path:
    """Pin ML runtime caches under project_root/js_reverse_cache/_runtime.

    This function is explicit because case entries may not create files on
    import. Call it before importing torch or ultralytics.
    """

    root = project_root.resolve()
    runtime = root / "js_reverse_cache" / "_runtime"
    for sub in ("torch", "hf", "ultralytics", "mpl", "xdg", "datasets", "weights", "runs"):
        (runtime / sub).mkdir(parents=True, exist_ok=True)

    os.environ["TORCH_HOME"] = str(runtime / "torch")
    os.environ["HF_HOME"] = str(runtime / "hf")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(runtime / "hf")
    os.environ["YOLO_CONFIG_DIR"] = str(runtime / "ultralytics")
    os.environ["MPLCONFIGDIR"] = str(runtime / "mpl")
    os.environ["XDG_CACHE_HOME"] = str(runtime / "xdg")
    os.environ["ULTRALYTICS_OFFLINE"] = "1"

    config_dir = runtime / "ultralytics" / "Ultralytics"
    config_dir.mkdir(parents=True, exist_ok=True)
    settings_path = config_dir / "settings.json"
    settings = {
        "settings_version": "0.0.6",
        "datasets_dir": str(runtime / "datasets"),
        "weights_dir": str(runtime / "weights"),
        "runs_dir": str(runtime / "runs"),
        "sync": False,
        "hub": False,
        "clearml": False,
        "comet": False,
        "dvc": False,
        "mlflow": False,
        "neptune": False,
        "raytune": False,
        "tensorboard": False,
        "wandb": False,
    }
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return runtime


def install_model_pack(project_root: Path) -> Dict[str, str]:
    """Copy the hash-verified model pack into a project without network use."""

    verify_model_assets()
    destination = project_root.resolve() / "models" / "geetest-v4-nine-grid"
    destination.mkdir(parents=True, exist_ok=True)
    targets = {
        MODEL_PATH: destination / "geetest_nine_model.pt",
        LABELS_PATH: destination / "labels.txt",
        MODEL_MANIFEST_PATH: destination / "MODEL.json",
    }
    for source, target in targets.items():
        shutil.copy2(source, target)

    copied_model_sha = sha256_file(targets[MODEL_PATH])
    copied_labels_sha = sha256_file(targets[LABELS_PATH])
    manifest = load_model_manifest()
    if copied_model_sha != manifest["model"]["sha256"]:
        raise RuntimeError("installed model SHA-256 mismatch")
    if copied_labels_sha != manifest["labels"]["sha256"]:
        raise RuntimeError("installed labels SHA-256 mismatch")

    return {
        "model": str(targets[MODEL_PATH]),
        "labels": str(targets[LABELS_PATH]),
        "manifest": str(targets[MODEL_MANIFEST_PATH]),
    }


def indices_to_userresponse(indices: List[int], count: int = 3) -> List[List[int]]:
    if len(indices) != NEED:
        raise ValueError("nine-grid requires exactly three indices")
    if count <= 0 or any(index < 0 or index >= count * count for index in indices):
        raise ValueError("grid index outside valid range")
    return [[index // count + 1, index % count + 1] for index in indices]


def decode_uri_bytes(raw: str) -> bytes:
    reserved = b";/?:@&=+$,#"
    result = bytearray()
    index = 0
    while index < len(raw):
        if raw[index] == "%" and index + 2 < len(raw):
            value = int(raw[index + 1:index + 3], 16)
            if value in reserved:
                result.extend(raw[index:index + 3].encode("ascii"))
            else:
                result.append(value)
            index += 3
        else:
            result.extend(raw[index].encode("utf-8"))
            index += 1
    return bytes(result)


def decode_string_table(source: str) -> List[str]:
    match = re.search(r"decodeURI\((['\"])(.*?)\1\)", source, re.S)
    if not match:
        raise ValueError("decodeURI string table not found")
    encoded = decode_uri_bytes(match.group(2))
    key_match = re.search(
        r"\}\((['\"])([^'\"]+)\1\)",
        source[match.end():match.end() + 4000],
    )
    if not key_match:
        raise ValueError("string-table XOR key not found")
    key = key_match.group(2).encode("latin1")
    decoded = bytes(value ^ key[index % len(key)] for index, value in enumerate(encoded))
    return decoded.decode("latin1").split("^")


def extract_bundle_metadata(source: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    strings = decode_string_table(source)
    lot_match = re.search(
        r'["\'](n\[[^"\']+)["\']\s*:\s*[^\n]*?\((\d+)\)',
        source,
    )
    if not lot_match:
        raise ValueError("lot rule not found")
    region = source[max(0, lot_match.start() - 5000):lot_match.end() + 500]
    fixed_match = re.search(
        r'\]\s*=\s*\{\s*([A-Za-z_$][A-Za-z0-9_$]*):\s*[^\n]*?\((\d+)\)\s*\}',
        region,
    )
    if not fixed_match:
        raise ValueError("fixed bundle field not found")
    return (
        {fixed_match.group(1): strings[int(fixed_match.group(2))]},
        {lot_match.group(1): strings[int(lot_match.group(2))]},
    )


def resolve_lot_expression(expression: str, lot_number: str) -> str:
    def replace(match: re.Match[str]) -> str:
        start, end = int(match.group(1)), int(match.group(2))
        return lot_number[start:end + 1]

    return re.sub(r"n\[(\d+):(\d+)\]", replace, expression).replace("+", "")


def resolve_lot_fields(lot_number: str, rules: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key_expression, value_expression in rules.items():
        path = resolve_lot_expression(key_expression, lot_number).split(".")
        value = resolve_lot_expression(value_expression, lot_number)
        target = result
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value
    return result


def int32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value if value < 0x80000000 else value - 0x100000000


def djb2_5381(value: str) -> int:
    state = 5381
    utf16 = value.encode("utf-16-le", "surrogatepass")
    for index in range(0, len(utf16), 2):
        code_unit = int.from_bytes(utf16[index:index + 2], "little")
        state = int32(state) * 33 + code_unit
    return int32(state) & 0x7FFFFFFF


def extract_function(source: str, start: int) -> str:
    brace = source.find("{", start)
    if brace < 0:
        raise ValueError("function opening brace not found")
    depth = 0
    quote: Optional[str] = None
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError("function closing brace not found")


def calculate_biht(gct_source: str) -> str:
    marker = gct_source.find("=5381;")
    if marker < 0:
        raise ValueError("GCT 5381 marker not found")
    hash_start = gct_source.rfind("function ", 0, marker)
    if hash_start < 0:
        raise ValueError("GCT hash function not found")
    hash_source = extract_function(gct_source, hash_start)
    hash_end = hash_start + len(hash_source)
    guard_match = re.search(r"function\s+\w+\(\w+\)\{", gct_source[hash_end:])
    if not guard_match:
        raise ValueError("GCT guard function not found")
    guard_source = extract_function(gct_source, hash_end + guard_match.start())
    strings = decode_string_table(gct_source)
    suffix = strings[78] if len(strings) > 78 else ""
    return str(djb2_5381(guard_source + str(djb2_5381(hash_source)))) + suffix


def verify_pow_message(message: str, digest: str, bits: int) -> bool:
    computed = hashlib.sha256(message.encode("utf-8")).hexdigest()
    target = 1 << (256 - bits)
    return computed == digest and int(digest, 16) < target


def solve_pow(
    captcha_id: str,
    lot_number: str,
    detail: Dict[str, Any],
    nonce_factory: Optional[Any] = None,
) -> Dict[str, str]:
    hashfunc = str(detail["hashfunc"]).lower()
    if hashfunc != "sha256":
        raise ValueError(f"unsupported PoW hash: {hashfunc}")
    prefix = (
        f"{detail['version']}|{detail['bits']}|{hashfunc}|{detail['datetime']}|"
        f"{captcha_id}|{lot_number}||"
    )
    create_nonce = nonce_factory or (lambda: secrets.token_hex(8))
    while True:
        message = prefix + str(create_nonce())
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
        if int(digest, 16) < 1 << (256 - int(detail["bits"])):
            return {"pow_msg": message, "pow_sign": digest}


def encrypt_aes(payload: Dict[str, Any], aes_key: bytes) -> Tuple[str, str]:
    if len(aes_key) != 16:
        raise ValueError("AES key must be 16 bytes")
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    ciphertext = AES.new(aes_key, AES.MODE_CBC, AES_IV).encrypt(
        pad(compact.encode("utf-8"), AES.block_size)
    )
    return ciphertext.hex(), compact


def encrypt_w(payload: Dict[str, Any], aes_key: Optional[bytes] = None) -> Tuple[str, str]:
    key = aes_key or secrets.token_hex(8).encode("ascii")
    aes_hex, compact = encrypt_aes(payload, key)
    public_key = RSA.construct((int(RSA_N_HEX, 16), RSA_E))
    rsa_hex = PKCS1_v1_5.new(public_key).encrypt(key).hex()
    return aes_hex + rsa_hex, compact


def _load_model(project_root: Path) -> Any:
    verify_model_assets()
    configure_runtime_cache(project_root)
    from ultralytics import YOLO

    return YOLO(str(MODEL_PATH), task="classify")


def _classify(model: Any, path: Path) -> Tuple[Dict[str, float], str]:
    result = next(iter(model.predict(source=str(path), imgsz=96, device="cpu", verbose=False)))
    names = result.names
    probabilities = result.probs.data.tolist()
    table = {names[index]: float(probabilities[index]) for index in range(len(probabilities))}
    return table, names[int(result.probs.top1)]


def recognize_cache(
    cache_dir: Path,
    project_root: Path,
    save_output: bool = True,
) -> Dict[str, Any]:
    cache = cache_dir.resolve()
    manifest_path = cache / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    count = int(manifest.get("image_meta", {}).get("count", 3))
    question_paths = sorted(cache.glob("ques_*_white.jpg")) or sorted(cache.glob("ques_*.png"))
    if not question_paths:
        raise FileNotFoundError("question image not found")

    model = _load_model(project_root)
    question_probabilities, question_top1 = _classify(model, question_paths[0])

    tiles: List[Dict[str, Any]] = []
    for index in range(count * count):
        path = cache / f"tile_{index}.jpg"
        if not path.exists():
            raise FileNotFoundError(f"tile missing: {path.name}")
        probabilities, top1 = _classify(model, path)
        tiles.append(
            {
                "index": index,
                "top1": top1,
                "top1Confidence": probabilities[top1],
                "probabilities": probabilities,
            }
        )

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for tile in tiles:
        grouped.setdefault(tile["top1"], []).append(tile)
    exact_groups = {label: members for label, members in grouped.items() if len(members) == NEED}

    if len(exact_groups) == 1:
        target = next(iter(exact_groups))
        selected = exact_groups[target]
        strategy = "tile-consensus"
    elif len(exact_groups) > 1:
        target = max(exact_groups, key=lambda label: question_probabilities.get(label, 0.0))
        selected = exact_groups[target]
        strategy = "tile-consensus-question-tiebreak"
    else:
        target = question_top1
        ranked = sorted(
            tiles,
            key=lambda tile: tile["probabilities"].get(target, 0.0),
            reverse=True,
        )
        if ranked[0]["probabilities"].get(target, 0.0) < 0.05:
            largest = max(grouped.values(), key=len)
            target = largest[0]["top1"]
            selected = sorted(
                largest,
                key=lambda tile: tile["top1Confidence"],
                reverse=True,
            )[:NEED]
            strategy = "largest-tile-group-fallback"
        else:
            selected = ranked[:NEED]
            strategy = "question-target-confidence"

    indices = sorted(tile["index"] for tile in selected)
    result = {
        "target": target,
        "indices": indices,
        "userresponse": indices_to_userresponse(indices, count),
        "strategy": strategy,
        "questionTop1": question_top1,
        "groupSizes": {label: len(members) for label, members in grouped.items()},
    }
    if save_output:
        (cache / "recognize.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Geetest GT4 nine-grid case helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("info", help="verify and print bundled model metadata")

    install_parser = subparsers.add_parser("install-model", help="copy model assets into a project")
    install_parser.add_argument("project_root", type=Path)

    recognize_parser = subparsers.add_parser("recognize", help="recognize an already collected cache")
    recognize_parser.add_argument("cache_dir", type=Path)
    recognize_parser.add_argument("project_root", type=Path)

    args = parser.parse_args(argv)
    if args.command == "info":
        print(json.dumps(verify_model_assets(), indent=2))
        return 0
    if args.command == "install-model":
        print(json.dumps(install_model_pack(args.project_root), indent=2))
        return 0
    if args.command == "recognize":
        print(json.dumps(recognize_cache(args.cache_dir, args.project_root), ensure_ascii=False, indent=2))
        return 0
    raise RuntimeError("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
