#!/usr/bin/env python3
"""Run the eval + improve loop until all pass or max iterations reached.

Combines run_eval.py and improve_description.py in a loop, tracking history
and returning the best description found. Supports train/test split to prevent
overfitting.
"""

import argparse
import json
import math
import random
import sys
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_report import generate_html
from scripts.improve_description import improve_description
from scripts.run_eval import find_project_root, run_eval
from scripts.utils import parse_skill_md


def split_eval_set(eval_set: list[dict], holdout: float, seed: int = 42) -> tuple[list[dict], list[dict]]:
    """Split eval set into train and test sets, stratified by should_trigger."""
    if not 0.0 < holdout < 1.0:
        raise ValueError("holdout must be greater than 0 and less than 1")
    queries = [item.get("query") for item in eval_set]
    if any(not isinstance(query, str) or not query.strip() for query in queries):
        raise ValueError("every eval item must have a non-empty query")
    if len(set(queries)) != len(queries):
        raise ValueError("eval query text must be unique before train/holdout splitting")
    random.seed(seed)

    # Separate by should_trigger
    trigger = [e for e in eval_set if e["should_trigger"]]
    no_trigger = [e for e in eval_set if not e["should_trigger"]]
    if len(trigger) < 2 or len(no_trigger) < 2:
        raise ValueError("holdout mode requires at least two positive and two negative queries")

    # Shuffle each group
    random.shuffle(trigger)
    random.shuffle(no_trigger)

    # Calculate split points
    n_trigger_test = min(len(trigger) - 1, max(1, int(len(trigger) * holdout)))
    n_no_trigger_test = min(len(no_trigger) - 1, max(1, int(len(no_trigger) * holdout)))

    # Split
    test_set = trigger[:n_trigger_test] + no_trigger[:n_no_trigger_test]
    train_set = trigger[n_trigger_test:] + no_trigger[n_no_trigger_test:]

    return train_set, test_set


def conservative_accuracy(results: list[dict]) -> tuple[float, float, int]:
    """Return observed accuracy and a 95% Wilson lower bound."""
    correct = 0
    total = 0
    for result in results:
        hits = result["triggers"] if result["should_trigger"] else result["runs"] - result["triggers"]
        correct += hits
        total += result["runs"]
    if total == 0:
        return 0.0, 0.0, 0
    accuracy = correct / total
    z = 1.96
    denominator = 1.0 + z * z / total
    center = accuracy + z * z / (2.0 * total)
    margin = z * math.sqrt((accuracy * (1.0 - accuracy) + z * z / (4.0 * total)) / total)
    return accuracy, max(0.0, (center - margin) / denominator), total


def prompt_regressions(baseline: list[dict], candidate: list[dict]) -> list[str]:
    baseline_by_query = {item["query"]: item for item in baseline}
    return sorted(
        item["query"]
        for item in candidate
        if baseline_by_query.get(item["query"], {}).get("pass") and not item.get("pass")
    )


def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    description_override: Optional[str],
    num_workers: int,
    timeout: int,
    max_iterations: int,
    runs_per_query: int,
    trigger_threshold: float,
    holdout: float,
    model: str,
    verbose: bool,
    min_effect: float = 0.02,
    live_report_path: Optional[Path] = None,
    log_dir: Optional[Path] = None,
) -> dict:
    """Run the eval + improvement loop."""
    if not 0.0 < min_effect <= 1.0:
        raise ValueError("min_effect must be greater than 0 and at most 1")
    if not 1 <= num_workers <= 32 or not 1 <= timeout <= 1800 or not 1 <= max_iterations <= 20 or not 2 <= runs_per_query <= 20:
        raise ValueError("workers must be 1..32, timeout 1..1800, iterations 1..20, and runs_per_query 2..20")
    if not 0.0 < trigger_threshold <= 1.0:
        raise ValueError("trigger_threshold must be greater than 0 and at most 1")
    if not 0.0 < holdout < 1.0:
        raise ValueError("holdout must be greater than 0 and less than 1")
    project_root = find_project_root()
    name, original_description, content = parse_skill_md(skill_path)
    current_description = description_override or original_description

    train_set, test_set = split_eval_set(eval_set, holdout)
    if verbose:
        print(f"Split: {len(train_set)} train, {len(test_set)} test (holdout={holdout})", file=sys.stderr)

    history = []
    exit_reason = "unknown"

    for iteration in range(1, max_iterations + 1):
        if verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Iteration {iteration}/{max_iterations}", file=sys.stderr)
            print(f"Description: {current_description}", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

        t0 = time.time()
        all_results = run_eval(
            eval_set=train_set,
            skill_name=name,
            description=current_description,
            num_workers=num_workers,
            timeout=timeout,
            project_root=project_root,
            runs_per_query=runs_per_query,
            trigger_threshold=trigger_threshold,
            model=model,
        )
        eval_elapsed = time.time() - t0

        train_result_list = all_results["results"]

        train_passed = sum(1 for r in train_result_list if r["pass"])
        train_total = len(train_result_list)
        train_summary = {"passed": train_passed, "failed": train_total - train_passed, "total": train_total}
        train_results = {"results": train_result_list, "summary": train_summary}

        history.append({
            "iteration": iteration,
            "description": current_description,
            "train_passed": train_summary["passed"],
            "train_failed": train_summary["failed"],
            "train_total": train_summary["total"],
            "train_results": train_results["results"],
            "test_passed": None,
            "test_failed": None,
            "test_total": None,
            "test_results": None,
            # For backward compat with report generator
            "passed": train_summary["passed"],
            "failed": train_summary["failed"],
            "total": train_summary["total"],
            "results": train_results["results"],
        })

        # Write live report if path provided
        if live_report_path:
            partial_output = {
                "original_description": original_description,
                "best_description": current_description,
                "best_score": "in progress",
                "iterations_run": len(history),
                "holdout": holdout,
                "train_size": len(train_set),
                "test_size": len(test_set),
                "history": history,
            }
            live_report_path.write_text(generate_html(partial_output, auto_refresh=True, skill_name=name), encoding="utf-8")

        if verbose:
            def print_eval_stats(label, results, elapsed):
                pos = [r for r in results if r["should_trigger"]]
                neg = [r for r in results if not r["should_trigger"]]
                tp = sum(r["triggers"] for r in pos)
                pos_runs = sum(r["runs"] for r in pos)
                fn = pos_runs - tp
                fp = sum(r["triggers"] for r in neg)
                neg_runs = sum(r["runs"] for r in neg)
                tn = neg_runs - fp
                total = tp + tn + fp + fn
                precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
                accuracy = (tp + tn) / total if total > 0 else 0.0
                print(f"{label}: {tp+tn}/{total} correct, precision={precision:.0%} recall={recall:.0%} accuracy={accuracy:.0%} ({elapsed:.1f}s)", file=sys.stderr)
                for r in results:
                    status = "PASS" if r["pass"] else "FAIL"
                    rate_str = f"{r['triggers']}/{r['runs']}"
                    print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:60]}", file=sys.stderr)

            print_eval_stats("Train", train_results["results"], eval_elapsed)
        if train_summary["failed"] == 0:
            exit_reason = f"all_passed (iteration {iteration})"
            if verbose:
                print(f"\nAll train queries passed on iteration {iteration}!", file=sys.stderr)
            break

        if iteration == max_iterations:
            exit_reason = f"max_iterations ({max_iterations})"
            if verbose:
                print(f"\nMax iterations reached ({max_iterations}).", file=sys.stderr)
            break

        # Improve the description based on train results
        if verbose:
            print(f"\nImproving description...", file=sys.stderr)

        t0 = time.time()
        # Strip test scores from history so improvement model can't see them
        blinded_history = [
            {k: v for k, v in h.items() if not k.startswith("test_")}
            for h in history
        ]
        new_description = improve_description(
            skill_name=name,
            skill_content=content,
            current_description=current_description,
            eval_results=train_results,
            history=blinded_history,
            model=model,
            log_dir=log_dir,
            iteration=iteration,
        )
        improve_elapsed = time.time() - t0

        if verbose:
            print(f"Proposed ({improve_elapsed:.1f}s): {new_description}", file=sys.stderr)

        current_description = new_description

    # Rank candidates on train data only, then open the holdout exactly once
    # for the baseline and selected candidate.
    ranking_key = "train_results"
    baseline = history[0]
    ranked = []
    for item in history:
        accuracy, lower_bound, samples = conservative_accuracy(item[ranking_key] or [])
        ranked.append((lower_bound, accuracy, -item["iteration"], -len(item["description"]), samples, item))
    candidate = max(ranked, key=lambda value: value[:4])[-1]

    def evaluate_holdout(item):
        held_out = run_eval(
            eval_set=test_set,
            skill_name=name,
            description=item["description"],
            num_workers=num_workers,
            timeout=timeout,
            project_root=project_root,
            runs_per_query=runs_per_query,
            trigger_threshold=trigger_threshold,
            model=model,
        )
        item["test_results"] = held_out["results"]
        item["test_passed"] = held_out["summary"]["passed"]
        item["test_failed"] = held_out["summary"]["failed"]
        item["test_total"] = held_out["summary"]["total"]

    evaluate_holdout(baseline)
    if candidate is not baseline:
        evaluate_holdout(candidate)

    baseline_accuracy, baseline_lower, _ = conservative_accuracy(baseline["test_results"] or [])
    candidate_accuracy, candidate_lower, candidate_samples = conservative_accuracy(candidate["test_results"] or [])
    regressions = prompt_regressions(baseline["train_results"] or [], candidate["train_results"] or [])
    regressions.extend(prompt_regressions(baseline["test_results"] or [], candidate["test_results"] or []))
    regressions = sorted(set(regressions))
    if candidate is baseline:
        best = baseline
        selection_reason = "baseline retained: no candidate ranked higher"
    elif regressions:
        best = baseline
        selection_reason = "baseline retained: candidate regressed previously passing prompts"
    elif candidate_lower < baseline_lower + min_effect:
        best = baseline
        selection_reason = "baseline retained: conservative improvement below min_effect"
    else:
        best = candidate
        selection_reason = "candidate accepted: conservative gain met threshold with no prompt regressions"
    best_score = f"{best['test_passed']}/{best['test_total']}"

    if verbose:
        print(f"\nExit reason: {exit_reason}", file=sys.stderr)
        print(f"Best score: {best_score} (iteration {best['iteration']})", file=sys.stderr)

    return {
        "exit_reason": exit_reason,
        "original_description": original_description,
        "best_description": best["description"],
        "best_iteration": best["iteration"],
        "best_score": best_score,
        "selection_reason": selection_reason,
        "min_effect": min_effect,
        "baseline_accuracy": baseline_accuracy,
        "baseline_lower_bound": baseline_lower,
        "candidate_accuracy": candidate_accuracy,
        "candidate_lower_bound": candidate_lower,
        "candidate_samples": candidate_samples,
        "prompt_regressions": regressions,
        "best_train_score": f"{best['train_passed']}/{best['train_total']}",
        "best_test_score": f"{best['test_passed']}/{best['test_total']}",
        "final_description": current_description,
        "iterations_run": len(history),
        "holdout": holdout,
        "train_size": len(train_set),
        "test_size": len(test_set),
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description="Run eval + improve loop")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override starting description")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max improvement iterations")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--holdout", type=float, default=0.4, help="Fraction of eval set reserved for final testing")
    parser.add_argument("--min-effect", type=float, default=0.02, help="Minimum conservative accuracy gain required to accept a candidate")
    parser.add_argument("--model", required=True, help="Model for improvement")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    parser.add_argument("--report", default="auto", help="Generate HTML report at this path (default: 'auto' for temp file, 'none' to disable)")
    parser.add_argument("--results-dir", default=None, help="Save all outputs (results.json, report.html, log.txt) to a timestamped subdirectory here")
    parser.add_argument("--confirm-run", action="store_true", help="Confirm worker/model execution and result generation")
    args = parser.parse_args()

    if not args.confirm_run:
        print("Error: refusing to spawn optimization workers without --confirm-run", file=sys.stderr)
        sys.exit(2)
    if not 0.0 < args.min_effect <= 1.0:
        print("Error: --min-effect must be greater than 0 and at most 1", file=sys.stderr)
        sys.exit(2)
    if not 1 <= args.num_workers <= 32 or not 1 <= args.timeout <= 1800 or not 1 <= args.max_iterations <= 20 or not 2 <= args.runs_per_query <= 20:
        print("Error: workers must be 1..32, timeout 1..1800, iterations 1..20, and runs-per-query 2..20", file=sys.stderr)
        sys.exit(2)
    if not 0.0 < args.trigger_threshold <= 1.0 or not 0.0 < args.holdout < 1.0:
        print("Error: trigger-threshold must be in (0,1] and holdout in (0,1)", file=sys.stderr)
        sys.exit(2)

    eval_set = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, _, _ = parse_skill_md(skill_path)

    # Set up live report path
    if args.report != "none":
        if args.report == "auto":
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            live_report_path = Path(tempfile.gettempdir()) / f"skill_description_report_{skill_path.name}_{timestamp}.html"
        else:
            live_report_path = Path(args.report)
        # Open the report immediately so the user can watch
        live_report_path.write_text("<html><body><h1>Starting optimization loop...</h1><meta http-equiv='refresh' content='5'></body></html>", encoding="utf-8")
        webbrowser.open(str(live_report_path))
    else:
        live_report_path = None

    # Determine output directory (create before run_loop so logs can be written)
    if args.results_dir:
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        results_dir = Path(args.results_dir) / timestamp
        results_dir.mkdir(parents=True, exist_ok=True)
    else:
        results_dir = None

    log_dir = results_dir / "logs" if results_dir else None

    output = run_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        description_override=args.description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        max_iterations=args.max_iterations,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        holdout=args.holdout,
        model=args.model,
        verbose=args.verbose,
        min_effect=args.min_effect,
        live_report_path=live_report_path,
        log_dir=log_dir,
    )

    # Save JSON output
    json_output = json.dumps(output, indent=2)
    print(json_output)
    if results_dir:
        (results_dir / "results.json").write_text(json_output, encoding="utf-8")

    # Write final HTML report (without auto-refresh)
    if live_report_path:
        live_report_path.write_text(generate_html(output, auto_refresh=False, skill_name=name), encoding="utf-8")
        print(f"\nReport: {live_report_path}", file=sys.stderr)

    if results_dir and live_report_path:
        (results_dir / "report.html").write_text(generate_html(output, auto_refresh=False, skill_name=name), encoding="utf-8")

    if results_dir:
        print(f"Results saved to: {results_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
