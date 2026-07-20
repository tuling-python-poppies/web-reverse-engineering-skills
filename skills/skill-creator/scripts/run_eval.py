#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes OpenCode to load the skill for a
set of queries. Outputs results as JSON.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.utils import parse_skill_md


SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def opencode_executable() -> str:
    return "opencode.cmd" if os.name == "nt" else "opencode"


def find_project_root() -> Path:
    """Find a sensible project root for `opencode run --dir`."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".git").is_dir():
            return parent
    return current


_SAFE_ENVIRONMENT_KEYS = {
    "APPDATA",
    "COLORTERM",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LANGUAGE",
    "LOCALAPPDATA",
    "NO_COLOR",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "SYSTEMROOT",
    "TEMP",
    "TERM",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
}


def build_restricted_environment(
    config_home: Path,
    source: Optional[Mapping[str, str]] = None,
) -> dict:
    """Build the minimal process environment needed to launch OpenCode."""
    source = os.environ if source is None else source
    env = {key: value for key, value in source.items() if key.upper() in _SAFE_ENVIRONMENT_KEYS}
    isolated_home = config_home.parent / "home"
    data_home = config_home.parent / "data"
    state_home = config_home.parent / "state"
    cache_home = config_home.parent / "cache"
    for directory in (isolated_home, data_home, state_home, cache_home):
        directory.mkdir(parents=True, exist_ok=True)
    for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"):
        env[key] = str(isolated_home)
    home_drive, home_path = os.path.splitdrive(str(isolated_home))
    if home_drive:
        env["HOMEDRIVE"] = home_drive
        env["HOMEPATH"] = home_path
    env["XDG_CONFIG_HOME"] = str(config_home)
    env["XDG_DATA_HOME"] = str(data_home)
    env["XDG_STATE_HOME"] = str(state_home)
    env["XDG_CACHE_HOME"] = str(cache_home)
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "true"
    return env


def copy_opencode_credentials(source: Mapping[str, str], data_home: Path) -> None:
    """Copy only OpenCode's credential store, never global skills/config/state."""
    source_home_value = source.get("HOME") or source.get("USERPROFILE")
    if not source_home_value:
        return
    source_home = Path(source_home_value)
    source_data = Path(source.get("XDG_DATA_HOME", source_home / ".local" / "share"))
    auth_file = source_data / "opencode" / "auth.json"
    if not auth_file.is_file() or auth_file.is_symlink():
        return
    destination = data_home / "opencode" / "auth.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(auth_file, destination)


def write_restricted_config(config_home: Path, allowed_skills: Sequence[str] = ()) -> Path:
    """Write deny-by-default OpenCode permissions into an isolated config home."""
    config_dir = config_home / "opencode"
    config_dir.mkdir(parents=True, exist_ok=True)
    permission: Dict[str, Any] = {"*": "deny"}
    if allowed_skills:
        permission["skill"] = {
            "*": "deny",
            **{skill_name: "allow" for skill_name in allowed_skills},
        }
    config_path = config_dir / "opencode.json"
    config_path.write_text(json.dumps({"permission": permission}), encoding="utf-8")
    return config_path


def _build_temp_skill_md(skill_name: str, skill_description: str) -> str:
    """Build a minimal SKILL.md for trigger evaluation."""
    indented_desc = "\n  ".join(skill_description.split("\n"))
    return (
        "---\n"
        f"name: {skill_name}\n"
        "description: |\n"
        f"  {indented_desc}\n"
        "---\n\n"
        f"# {skill_name}\n\n"
        "Temporary skill used only for trigger evaluation.\n"
    )


def _parse_triggered(output: str, skill_name: str) -> bool:
    """Return whether OpenCode loaded the temporary skill."""
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") != "tool_use":
            continue

        part = event.get("part", {})
        if part.get("tool") != "skill":
            continue

        state = part.get("state", {})
        tool_input = state.get("input", {})
        if tool_input.get("name") == skill_name:
            return True

    return False


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: Optional[str] = None,
) -> bool:
    """Run a single query and return whether the temporary skill was loaded."""
    if not SKILL_NAME_RE.fullmatch(skill_name):
        raise ValueError(f"invalid skill name: {skill_name!r}")
    with tempfile.TemporaryDirectory(prefix=f"opencode-skill-eval-") as temp_dir:
        temp_root = Path(temp_dir)
        xdg_config_home = temp_root / "config"
        workspace = temp_root / "workspace"
        workspace.mkdir()
        write_restricted_config(xdg_config_home, [skill_name])
        temp_skills_root = xdg_config_home / "opencode" / "skills"
        temp_skill_dir = temp_skills_root / skill_name
        if temp_skill_dir.resolve().parent != temp_skills_root.resolve():
            raise ValueError("temporary skill path escaped its isolated root")
        temp_skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = temp_skill_dir / "SKILL.md"
        skill_file.write_text(_build_temp_skill_md(skill_name, skill_description), encoding="utf-8")

        cmd = [
            opencode_executable(),
            "run",
            "--pure",
            "--format",
            "json",
            "--dir",
            str(workspace),
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["--", query])

        env = build_restricted_environment(xdg_config_home)
        copy_opencode_credentials(os.environ, Path(env["XDG_DATA_HOME"]))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=str(workspace),
                env=env,
            )
        except subprocess.TimeoutExpired:
            return False

        if result.returncode != 0:
            print(
                f"Warning: opencode run exited {result.returncode} for query {query!r}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False

        return _parse_triggered(result.stdout, skill_name)


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: Optional[str] = None,
) -> dict:
    """Run the full eval set and return results."""
    queries = [item.get("query") for item in eval_set]
    if any(not isinstance(query, str) or not query.strip() for query in queries):
        raise ValueError("every eval item must have a non-empty query")
    if len(set(queries)) != len(queries):
        raise ValueError("eval query text must be unique")
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for opencode run (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    parser.add_argument("--confirm-run", action="store_true", help="Confirm worker/model execution and result generation")
    args = parser.parse_args()

    if not args.confirm_run:
        print("Error: refusing to spawn eval workers without --confirm-run", file=sys.stderr)
        sys.exit(2)
    if not 1 <= args.num_workers <= 32 or not 1 <= args.timeout <= 1800 or not 1 <= args.runs_per_query <= 20:
        print("Error: workers must be 1..32, timeout 1..1800 seconds, and runs-per-query 1..20", file=sys.stderr)
        sys.exit(2)
    if not 0.0 < args.trigger_threshold <= 1.0:
        print("Error: trigger-threshold must be greater than 0 and at most 1", file=sys.stderr)
        sys.exit(2)

    eval_set = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
