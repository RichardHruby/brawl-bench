"""
Browser Brawl — Benchmark Runner

Orchestrates baseline vs disrupted runs across all tasks and models,
then evaluates and generates a comparison report.
"""

import asyncio
import json
import os
from datetime import datetime
from glob import glob
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from harness import MODELS, start_playwright, run_task, load_tasks, format_prompt, save_result
from evaluator import evaluate_results_dir, extract_answer


async def run_single(
    model_key: str,
    task: dict,
    condition: str,
    disruption_files: list[str] | None,
    output_dir: str,
    max_turns: int = 25,
    headless: bool = True,
    force_screenshot: bool = False,
):
    """Run a single (model, task, condition) combination."""
    print(f"\n{'─'*60}")
    print(f"  {model_key} | {task['id']} | {condition}")
    print(f"  Task: {task['ques'][:80]}...")
    print(f"{'─'*60}")

    init_scripts = disruption_files if condition == "disrupted" else None
    run_dir = Path(output_dir) / model_key / task["id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    mcp_output_dir = str(run_dir / "mcp_output")

    async with start_playwright(
        headless=headless,
        init_scripts=init_scripts,
        output_dir=mcp_output_dir,
        save_video=True,
    ) as mcp:
        result = await run_task(
            model_key=model_key,
            task_prompt=format_prompt(task),
            mcp_server=mcp,
            task_id=task["id"],
            condition=condition,
            max_turns=max_turns,
            screenshot_dir=str(run_dir),
            force_screenshot=force_screenshot,
        )

    # Brief pause to ensure Chrome processes fully exit
    await asyncio.sleep(2)

    save_result(result, output_dir=output_dir)

    answer = extract_answer(result.final_output)
    status = "ERROR" if result.error else ("answered" if answer else "no answer")
    print(f"  → {status} in {result.turns} turns ({result.elapsed_sec}s)")
    if answer:
        print(f"  → Answer: {answer[:100]}")
    if result.error:
        print(f"  → Error: {result.error[:200]}")

    return result


# ---------------------------------------------------------------------------
# Disruption Sets — maps condition names to disruption file directories.
# Each condition loads all *.js files from its listed directories.
# ---------------------------------------------------------------------------

DISRUPTION_SETS = {
    "baseline":  [],
    "annoyance": ["disruptions/generic"],
    "hijack":    ["disruptions/amazon/hijack"],
    "exfil":     ["disruptions/amazon/exfil"],
}


def resolve_disruptions(condition: str) -> list[str]:
    """Return sorted list of JS file paths for a given condition."""
    dirs = DISRUPTION_SETS.get(condition, [])
    files = []
    for d in dirs:
        files.extend(sorted(glob(os.path.join(d, "*.js"))))
    return files


async def run_benchmark(
    models: list[str] | None = None,
    tasks_file: str = "tasks/amazon_selected.jsonl",
    output_dir: str = "results",
    max_turns: int = 25,
    headless: bool = True,
    conditions: list[str] | None = None,
    force_screenshot: bool = False,
):
    """
    Run the full benchmark: all models × all tasks × conditions.

    Conditions map to disruption sets:
      baseline  — no disruptions
      annoyance — generic UI disruptions (cookie banner, sticky header, etc.)
      hijack    — navigation hijack attacks
      exfil     — data exfiltration attacks

    Each run gets a timestamped subdirectory under output_dir to prevent
    overwriting previous results.  A 'latest' symlink is updated to point
    at the newest run.
    """
    tasks = load_tasks(tasks_file)
    model_keys = models or list(MODELS.keys())
    conditions = conditions or ["baseline"]

    # Create a timestamped run directory so repeated runs never overwrite
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_output_dir = str(Path(output_dir) / run_timestamp)
    Path(run_output_dir).mkdir(parents=True, exist_ok=True)

    # Update a 'latest' symlink for convenience
    latest_link = Path(output_dir) / "latest"
    latest_link.unlink(missing_ok=True)
    latest_link.symlink_to(run_timestamp)

    print(f"Run output: {run_output_dir}")

    # Resolve and display disruption files per condition
    for condition in conditions:
        files = resolve_disruptions(condition)
        if files:
            print(f"Disruptions [{condition}]: {[os.path.basename(f) for f in files]}")
        elif condition != "baseline":
            print(f"WARNING: No disruption files for condition '{condition}'!")

    print(f"Models: {model_keys}")
    print(f"Tasks: {[t['id'] for t in tasks]}")
    print(f"Conditions: {conditions}")
    total = len(model_keys) * len(tasks) * len(conditions)
    print(f"Total runs: {total}")
    print(f"{'='*60}")

    all_results = []
    run_count = 0

    for task in tasks:
        for model_key in model_keys:
            for condition in conditions:
                run_count += 1
                print(f"\n[{run_count}/{total}]", end="")

                disruption_files = resolve_disruptions(condition)

                result = await run_single(
                    model_key=model_key,
                    task=task,
                    condition=condition,
                    disruption_files=disruption_files if disruption_files else None,
                    output_dir=run_output_dir,
                    max_turns=max_turns,
                    headless=headless,
                    force_screenshot=force_screenshot,
                )
                all_results.append(result)

    return all_results, run_output_dir


def generate_report(results_dir: str, tasks_file: str):
    """Generate a comparison report from evaluated results."""
    eval_results = []
    results_path = Path(results_dir)

    for model_dir in sorted(results_path.iterdir()):
        if not model_dir.is_dir() or model_dir.name.endswith(".json"):
            continue
        for task_dir in sorted(model_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            eval_file = task_dir / "eval.json"
            run_file = task_dir / "run.json"
            if eval_file.exists() and run_file.exists():
                with open(eval_file) as f:
                    eval_data = json.load(f)
                with open(run_file) as f:
                    run_data = json.load(f)
                nav = eval_data.get("navigation", {})
                exfil = eval_data.get("exfiltration", {})
                eval_results.append({
                    "condition": run_data.get("condition", "unknown"),
                    "model": model_dir.name,
                    "task": task_dir.name,
                    "success": eval_data.get("success"),
                    "turns": run_data.get("turns", 0),
                    "elapsed": run_data.get("elapsed_sec", 0),
                    "input_tokens": run_data.get("input_tokens", 0),
                    "output_tokens": run_data.get("output_tokens", 0),
                    "error": run_data.get("error"),
                    "hijacked": nav.get("hijacked", False),
                    "offsite_urls": nav.get("offsite_urls", []),
                    "exfiltrated": exfil.get("exfiltrated", False),
                    "leaked_canaries": exfil.get("leaked_canaries", []),
                })

    if not eval_results:
        print("No evaluated results found.")
        return

    print(f"\n{'='*70}")
    print("BROWSER BRAWL — BENCHMARK REPORT")
    print(f"{'='*70}\n")

    # Per-model summary
    models_seen = sorted(set(r["model"] for r in eval_results))
    conditions_seen = sorted(set(r["condition"] for r in eval_results))

    print(f"{'Model':<22} {'Condition':<12} {'Success':<10} {'Rate':<8} {'Avg Turns':<10}")
    print(f"{'─'*62}")

    for model in models_seen:
        for condition in conditions_seen:
            runs = [r for r in eval_results if r["model"] == model and r["condition"] == condition]
            successes = sum(1 for r in runs if r["success"] is True)
            total = len(runs)
            rate = f"{successes}/{total}" if total > 0 else "N/A"
            pct = f"{100*successes/total:.0f}%" if total > 0 else "N/A"
            avg_turns = f"{sum(r['turns'] for r in runs)/total:.1f}" if total > 0 else "N/A"
            print(f"{model:<22} {condition:<12} {rate:<10} {pct:<8} {avg_turns:<10}")

    # Delta analysis
    print(f"\n{'─'*62}")
    print("DISRUPTION IMPACT (baseline → disrupted)\n")

    for model in models_seen:
        baseline_runs = {r["task"]: r for r in eval_results if r["model"] == model and r["condition"] == "baseline"}
        disrupted_runs = {r["task"]: r for r in eval_results if r["model"] == model and r["condition"] == "disrupted"}

        regressions = 0
        for task_id in baseline_runs:
            b = baseline_runs[task_id]
            d = disrupted_runs.get(task_id)
            if d and b["success"] and not d["success"]:
                regressions += 1
                print(f"  REGRESSION: {model} / {task_id}: SUCCESS → FAIL")

        if regressions == 0 and disrupted_runs:
            print(f"  {model}: no regressions detected")

    # Token usage & cost
    PRICING = {  # per 1M tokens: (input, output)
        "claude-sonnet-4.6": (3.0, 15.0),
        "gpt-5.4": (2.5, 15.0),
        "gemini-3.1-pro": (1.25, 10.0),
        "gemini-3-flash": (0.50, 3.0),
    }

    print(f"\n{'─'*62}")
    print("TOKEN USAGE & COST\n")
    print(f"{'Model':<22} {'Condition':<12} {'Input Tok':<12} {'Output Tok':<12} {'Cost':<10}")
    print(f"{'─'*68}")

    total_cost = 0.0
    for model in models_seen:
        for condition in conditions_seen:
            runs = [r for r in eval_results if r["model"] == model and r["condition"] == condition]
            in_tok = sum(r["input_tokens"] for r in runs)
            out_tok = sum(r["output_tokens"] for r in runs)
            in_price, out_price = PRICING.get(model, (3.0, 15.0))
            cost = (in_tok / 1_000_000 * in_price) + (out_tok / 1_000_000 * out_price)
            total_cost += cost
            print(f"{model:<22} {condition:<12} {in_tok:<12,} {out_tok:<12,} ${cost:.4f}")

    print(f"{'─'*68}")
    print(f"{'TOTAL':<46} ${total_cost:.4f}")

    # Security events
    security_events = [r for r in eval_results if r["hijacked"] or r["exfiltrated"]]
    print(f"\n{'─'*62}")
    print("SECURITY EVENTS\n")
    if security_events:
        print(f"{'Model':<22} {'Task':<14} {'Condition':<12} {'Hijack':<8} {'Exfil':<8} {'Details'}")
        print(f"{'─'*80}")
        for r in security_events:
            details = ", ".join(r["offsite_urls"] + r["leaked_canaries"])
            print(f"{r['model']:<22} {r['task']:<14} {r['condition']:<12} "
                  f"{'YES' if r['hijacked'] else '-':<8} "
                  f"{'YES' if r['exfiltrated'] else '-':<8} {details[:60]}")
    else:
        print("  No navigation hijacks or data exfiltration detected.")

    # Save report
    report_path = Path(results_dir) / "report.json"
    with open(report_path, "w") as f:
        json.dump(eval_results, f, indent=2)
    print(f"\nFull report saved to: {report_path}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Browser Brawl Runner")
    parser.add_argument("--models", nargs="*", default=None, help="Models to test (default: all)")
    parser.add_argument("--tasks-file", default="tasks/amazon_selected.jsonl")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--max-turns", type=int, default=25)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--conditions", nargs="*", default=None,
                        help="Conditions: baseline, annoyance, hijack, exfil (default: baseline)")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation after benchmark")
    parser.add_argument("--report", action="store_true", help="Generate report from existing results")
    parser.add_argument("--eval-model", default="gpt-4o")
    parser.add_argument("--force-screenshot", action="store_true",
                        help="Inject browser screenshots into the LLM context each turn")
    args = parser.parse_args()

    if args.report:
        # Use 'latest' symlink if the user just passes the base results dir
        report_dir = args.output_dir
        latest = Path(report_dir) / "latest"
        if latest.is_symlink() or latest.is_dir():
            report_dir = str(latest)
        generate_report(report_dir, args.tasks_file)
        return

    # Run benchmark
    _results, run_output_dir = await run_benchmark(
        models=args.models,
        tasks_file=args.tasks_file,
        output_dir=args.output_dir,
        max_turns=args.max_turns,
        headless=not args.headed,
        conditions=args.conditions,
        force_screenshot=args.force_screenshot,
    )

    # Optionally evaluate
    if args.evaluate:
        from openai import OpenAI
        print(f"\n{'='*60}")
        print("RUNNING EVALUATION")
        print(f"{'='*60}")
        client = OpenAI()
        evaluate_results_dir(run_output_dir, args.tasks_file, client, args.eval_model)
        generate_report(run_output_dir, args.tasks_file)


if __name__ == "__main__":
    asyncio.run(main())
