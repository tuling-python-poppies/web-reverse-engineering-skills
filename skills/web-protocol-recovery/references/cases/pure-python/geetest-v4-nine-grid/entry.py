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
from typing import Any, Callable, Dict, List, Optional, Tuple

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad


CASE_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = CASE_ROOT / "assets"
MODEL_PATH = ASSETS_ROOT / "geetest_nine_model.pt"
LABELS_PATH = ASSETS_ROOT / "labels.txt"
MODEL_MANIFEST_PATH = ASSETS_ROOT / "MODEL.json"
MODEL_PACK_NAME = "geetest-v4-nine-grid"
MAX_POW_ATTEMPTS = 1_000_000

AES_IV = b"0000000000000000"
RSA_N_HEX = (
    "c1e3934d1614465b33053e7f48ee4ec87b14b95ef88947713d25eecbff7e74c"
    "7977d02dc1d9451f79dd5d1c10c29acb6a9b4d6fb7d0a0279b6719e1772565f"
    "09af627715919221aef91899cae08c0d686d748b20a3603be2318ca6bc2b597"
    "06592a9219d0bf05c9f65023a21d2330807252ae0066d59ceefa5f2748ea80bab81"
)
RSA_E = 65537
NEED = 3
GRID_COUNT = 3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_pack_paths(model_root: Path) -> Tuple[Path, Path, Path]:
    root = model_root.resolve()
    manifest_path = root / "MODEL.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def declared_path(field: str) -> Path:
        candidate = (root / str(manifest[field]["path"])).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"{field} path escapes model pack") from exc
        return candidate

    return declared_path("model"), declared_path("labels"), manifest_path


def load_model_manifest(model_root: Path = ASSETS_ROOT) -> Dict[str, Any]:
    return json.loads((model_root.resolve() / "MODEL.json").read_text(encoding="utf-8"))


def load_labels(path: Path = LABELS_PATH) -> List[str]:
    labels = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [label for label in labels if label and not label.startswith("#")]


def verify_model_assets(model_root: Path = ASSETS_ROOT) -> Dict[str, Any]:
    model_path, labels_path, _ = _model_pack_paths(model_root)
    manifest = load_model_manifest(model_root)
    expected_model = manifest["model"]
    expected_labels = manifest["labels"]
    actual_model_sha = sha256_file(model_path)
    actual_labels_sha = sha256_file(labels_path)
    actual_bytes = model_path.stat().st_size
    labels = load_labels(labels_path)

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

    return runtime


def apply_ultralytics_runtime_settings(settings: Any, runtime: Path) -> Dict[str, Any]:
    """Update only settings supported by the installed Ultralytics release."""

    paths = {
        "datasets_dir": str(runtime / "datasets"),
        "weights_dir": str(runtime / "weights"),
        "runs_dir": str(runtime / "runs"),
    }
    missing_paths = sorted(set(paths) - set(settings))
    if missing_paths:
        raise RuntimeError("Ultralytics settings missing path keys: " + ", ".join(missing_paths))
    disabled_integrations = {
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
        "vscode_msg": False,
        "openvino_msg": False,
    }
    desired = {**paths, **{key: value for key, value in disabled_integrations.items() if key in settings}}
    settings.update(desired)

    for key, expected in paths.items():
        if Path(str(settings[key])).resolve() != Path(expected).resolve():
            raise RuntimeError(f"Ultralytics setting {key} escaped the project runtime cache")
    enabled = [key for key in disabled_integrations if key in settings and settings[key] is not False]
    if enabled:
        raise RuntimeError("Ultralytics integrations remain enabled: " + ", ".join(enabled))
    return desired


def install_model_pack(project_root: Path) -> Dict[str, str]:
    """Copy the hash-verified model pack into a project without network use."""

    verify_model_assets(ASSETS_ROOT)
    source_model, source_labels, source_manifest = _model_pack_paths(ASSETS_ROOT)
    destination = project_root.resolve() / "models" / MODEL_PACK_NAME
    destination.mkdir(parents=True, exist_ok=True)
    targets = {
        source_model: destination / source_model.name,
        source_labels: destination / source_labels.name,
        source_manifest: destination / source_manifest.name,
    }
    for source, target in targets.items():
        shutil.copy2(source, target)

    copied_model_sha = sha256_file(targets[source_model])
    copied_labels_sha = sha256_file(targets[source_labels])
    manifest = load_model_manifest(ASSETS_ROOT)
    if copied_model_sha != manifest["model"]["sha256"]:
        raise RuntimeError("installed model SHA-256 mismatch")
    if copied_labels_sha != manifest["labels"]["sha256"]:
        raise RuntimeError("installed labels SHA-256 mismatch")

    return {
        "model": str(targets[source_model]),
        "labels": str(targets[source_labels]),
        "manifest": str(targets[source_manifest]),
    }


def select_model_pack(project_root: Path) -> Path:
    """Prefer a complete installed pack; fail closed on a partial install."""

    installed = project_root.resolve() / "models" / MODEL_PACK_NAME
    required = [installed / "MODEL.json", installed / "geetest_nine_model.pt", installed / "labels.txt"]
    present = [path.exists() for path in required]
    if all(present):
        return installed
    if any(present):
        missing = ", ".join(path.name for path, exists in zip(required, present) if not exists)
        raise RuntimeError(f"installed model pack is incomplete; missing: {missing}")
    return ASSETS_ROOT


def indices_to_userresponse(indices: List[int], count: int = 3) -> List[List[int]]:
    if len(indices) != NEED:
        raise ValueError("nine-grid requires exactly three indices")
    if len(set(indices)) != len(indices):
        raise ValueError("nine-grid indices must be unique")
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


def _pow_target(bits: Any) -> Tuple[int, int]:
    try:
        value = int(bits)
    except (TypeError, ValueError) as exc:
        raise ValueError("PoW bits must be an integer") from exc
    if value < 1 or value > 255:
        raise ValueError("PoW bits must be between 1 and 255")
    return value, 1 << (256 - value)


def verify_pow_message(message: str, digest: str, bits: int) -> bool:
    computed = hashlib.sha256(message.encode("utf-8")).hexdigest()
    _, target = _pow_target(bits)
    return computed == digest and int(digest, 16) < target


def solve_pow(
    captcha_id: str,
    lot_number: str,
    detail: Dict[str, Any],
    nonce_factory: Optional[Any] = None,
    max_attempts: int = MAX_POW_ATTEMPTS,
) -> Dict[str, str]:
    hashfunc = str(detail["hashfunc"]).lower()
    if hashfunc != "sha256":
        raise ValueError(f"unsupported PoW hash: {hashfunc}")
    _, target = _pow_target(detail["bits"])
    if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > MAX_POW_ATTEMPTS:
        raise ValueError(f"max_attempts must be between 1 and {MAX_POW_ATTEMPTS}")
    prefix = (
        f"{detail['version']}|{detail['bits']}|{hashfunc}|{detail['datetime']}|"
        f"{captcha_id}|{lot_number}||"
    )
    create_nonce = nonce_factory or (lambda: secrets.token_hex(8))
    for _ in range(max_attempts):
        message = prefix + str(create_nonce())
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
        if int(digest, 16) < target:
            return {"pow_msg": message, "pow_sign": digest}
    raise TimeoutError(f"PoW target not found within {max_attempts} attempts")


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


def _embedded_labels(model: Any) -> List[str]:
    names = getattr(model, "names", None)
    if isinstance(names, dict):
        try:
            return [str(names[index]) for index in range(len(names))]
        except KeyError as exc:
            raise RuntimeError("model class map must use contiguous integer keys") from exc
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    raise RuntimeError("model does not expose a class-name map")


def validate_model_class_names(model: Any, labels: List[str]) -> None:
    if _embedded_labels(model) != labels:
        raise RuntimeError("embedded model class map does not match labels.txt")


def _load_model(project_root: Path, allow_checkpoint_execution: bool = False) -> Tuple[Any, List[str]]:
    if not allow_checkpoint_execution:
        raise PermissionError(
            "PyTorch .pt checkpoints may execute serialized code; explicit per-run approval is required"
        )
    model_root = select_model_pack(project_root)
    model_path, labels_path, _ = _model_pack_paths(model_root)
    verify_model_assets(model_root)
    runtime = configure_runtime_cache(project_root)
    from ultralytics import YOLO, settings

    apply_ultralytics_runtime_settings(settings, runtime)
    model = YOLO(str(model_path), task="classify")
    labels = load_labels(labels_path)
    validate_model_class_names(model, labels)
    return model, labels


def _classify(model: Any, path: Path, labels: List[str]) -> Tuple[Dict[str, float], str]:
    result = next(iter(model.predict(source=str(path), imgsz=96, device="cpu", verbose=False)))
    probabilities = result.probs.data.tolist()
    if len(probabilities) != len(labels):
        raise RuntimeError("model probability count does not match labels.txt")
    top1 = int(result.probs.top1)
    if top1 < 0 or top1 >= len(labels):
        raise RuntimeError("model top1 index is outside labels.txt")
    table = {labels[index]: float(probabilities[index]) for index in range(len(probabilities))}
    return table, labels[top1]


def select_nine_grid_tiles(
    question_probabilities: Dict[str, float],
    question_top1: str,
    tiles: List[Dict[str, Any]],
    count: int,
) -> Dict[str, Any]:
    if count <= 0 or count * count < NEED:
        raise ValueError("grid size cannot supply three answers")
    if len(tiles) != count * count:
        raise ValueError("tile count does not match grid dimensions")
    indices = [int(tile["index"]) for tile in tiles]
    if len(set(indices)) != len(indices) or set(indices) != set(range(count * count)):
        raise ValueError("tiles must contain every grid index exactly once")
    for tile in tiles:
        top1 = str(tile["top1"])
        probabilities = tile.get("probabilities")
        if not isinstance(probabilities, dict) or top1 not in probabilities:
            raise ValueError("each tile must include its top1 probability")

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for tile in tiles:
        grouped.setdefault(str(tile["top1"]), []).append(tile)
    exact_groups = {label: members for label, members in grouped.items() if len(members) == NEED}

    if len(exact_groups) == 1:
        target = next(iter(exact_groups))
        selected = exact_groups[target]
        strategy = "tile-consensus"
    elif len(exact_groups) > 1:
        ranked_groups = sorted(
            exact_groups,
            key=lambda label: question_probabilities.get(label, 0.0),
            reverse=True,
        )
        best_score = question_probabilities.get(ranked_groups[0], 0.0)
        next_score = question_probabilities.get(ranked_groups[1], 0.0)
        if best_score < 0.05 or best_score == next_score:
            raise RuntimeError("question signal cannot disambiguate exact three-tile groups")
        target = ranked_groups[0]
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
            largest_size = max(map(len, grouped.values()))
            largest_groups = [members for members in grouped.values() if len(members) == largest_size]
            if len(largest_groups) != 1:
                raise RuntimeError("largest tile group is ambiguous")
            largest = largest_groups[0]
            if len(largest) < NEED:
                raise RuntimeError("no class supplies three candidate tiles")
            target = str(largest[0]["top1"])
            selected = sorted(
                largest,
                key=lambda tile: tile["top1Confidence"],
                reverse=True,
            )[:NEED]
            strategy = "largest-tile-group-fallback"
        else:
            if len(ranked) > NEED:
                accepted_score = ranked[NEED - 1]["probabilities"].get(target, 0.0)
                rejected_score = ranked[NEED]["probabilities"].get(target, 0.0)
                if accepted_score == rejected_score:
                    raise RuntimeError("question-target ranking is ambiguous at the answer boundary")
            selected = ranked[:NEED]
            strategy = "question-target-confidence"

    selected_indices = sorted(int(tile["index"]) for tile in selected)
    return {
        "target": target,
        "indices": selected_indices,
        "userresponse": indices_to_userresponse(selected_indices, count),
        "strategy": strategy,
        "questionTop1": question_top1,
        "groupSizes": {label: len(members) for label, members in grouped.items()},
    }


def recognize_cache(
    cache_dir: Path,
    project_root: Path,
    save_output: bool = True,
    allow_checkpoint_execution: bool = False,
    model_loader: Optional[Callable[[Path, bool], Tuple[Any, List[str]]]] = None,
    classifier: Optional[Callable[[Any, Path, List[str]], Tuple[Dict[str, float], str]]] = None,
) -> Dict[str, Any]:
    cache = cache_dir.resolve()
    allowed_cache_root = (project_root.resolve() / "js_reverse_cache").resolve()
    try:
        cache.relative_to(allowed_cache_root)
    except ValueError as exc:
        raise ValueError("cache_dir must be inside <projectRoot>/js_reverse_cache") from exc
    manifest_path = cache / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    count = int(manifest.get("image_meta", {}).get("count", GRID_COUNT))
    if count != GRID_COUNT:
        raise ValueError(f"this case requires nine_nums={GRID_COUNT}; fresh recovery is required")
    question_paths = sorted(cache.glob("ques_*_white.jpg")) or sorted(cache.glob("ques_*.png"))
    if not question_paths:
        raise FileNotFoundError("question image not found")
    tile_paths = [cache / f"tile_{index}.jpg" for index in range(count * count)]
    missing_tiles = [path.name for path in tile_paths if not path.exists()]
    if missing_tiles:
        raise FileNotFoundError("tile files missing: " + ", ".join(missing_tiles))

    load = model_loader or _load_model
    classify = classifier or _classify
    model, labels = load(project_root, allow_checkpoint_execution)
    question_probabilities, question_top1 = classify(model, question_paths[0], labels)

    tiles: List[Dict[str, Any]] = []
    for index, path in enumerate(tile_paths):
        probabilities, top1 = classify(model, path, labels)
        tiles.append(
            {
                "index": index,
                "top1": top1,
                "top1Confidence": probabilities[top1],
                "probabilities": probabilities,
            }
        )

    result = select_nine_grid_tiles(question_probabilities, question_top1, tiles, count)
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
    recognize_parser.add_argument(
        "--allow-checkpoint-execution",
        action="store_true",
        help="explicitly approve loading the hash-verified PyTorch pickle checkpoint",
    )

    args = parser.parse_args(argv)
    if args.command == "info":
        print(json.dumps(verify_model_assets(), indent=2))
        return 0
    if args.command == "install-model":
        print(json.dumps(install_model_pack(args.project_root), indent=2))
        return 0
    if args.command == "recognize":
        print(
            json.dumps(
                recognize_cache(
                    args.cache_dir,
                    args.project_root,
                    allow_checkpoint_execution=args.allow_checkpoint_execution,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    raise RuntimeError("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
