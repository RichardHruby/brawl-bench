"""
Browser Brawl — Benchmark Runner

Orchestrates baseline vs disrupted runs across all tasks and models,
then evaluates and generates a comparison report.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from glob import glob
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from harness import MODELS, start_playwright, run_task, load_tasks, format_prompt, save_result
from evaluator import evaluate_results_dir, extract_answer

logger = logging.getLogger(__name__)


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

    init_scripts = disruption_files if condition != "baseline" else None
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
    task_ids: list[str] | None = None,
    force_screenshot: bool = False,
    parallel: int = 1,
):
    """
    Run the full benchmark: all models × all tasks × conditions.

    Conditions map to disruption sets:
      baseline  — no disruptions
      hijack    — navigation hijack attacks
      exfil     — data exfiltration attacks

    Each run gets a timestamped subdirectory under output_dir to prevent
    overwriting previous results.  A 'latest' symlink is updated to point
    at the newest run.

    When parallel > 1, up to that many browser tasks run concurrently.
    Each task's failure is isolated — it never cancels sibling tasks.
    """
    tasks = load_tasks(tasks_file)
    if task_ids:
        tasks = [t for t in tasks if t["id"] in task_ids]
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

    # Persist run configuration (same schema as harness.py's config.json)
    config = {
        "timestamp": run_timestamp,
        "models": model_keys,
        "tasks_file": tasks_file,
        "task_ids": [t["id"] for t in tasks],
        "conditions": conditions,
        "disruptions": {c: resolve_disruptions(c) for c in conditions},
        "max_turns": max_turns,
        "headless": headless,
        "force_screenshot": force_screenshot,
        "parallel": parallel,
    }
    with open(Path(run_output_dir) / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"Run output: {run_output_dir}")

    # Resolve and display disruption files per condition
    for condition in conditions:
        files = resolve_disruptions(condition)
        if files:
            print(f"Disruptions [{condition}]: {[os.path.basename(f) for f in files]}")
        elif condition != "baseline":
            print(f"WARNING: No disruption files for condition '{condition}'!")

    # Build the full job list
    jobs = [
        (task, model_key, condition)
        for task in tasks
        for model_key in model_keys
        for condition in conditions
    ]

    print(f"Models: {model_keys}")
    print(f"Tasks: {[t['id'] for t in tasks]}")
    print(f"Conditions: {conditions}")
    print(f"Total runs: {len(jobs)} (parallel={parallel})")
    print(f"{'='*60}")

    if parallel <= 1:
        # Sequential mode — preserves original behavior exactly
        all_results = []
        for i, (task, model_key, condition) in enumerate(jobs, 1):
            print(f"\n[{i}/{len(jobs)}]", end="")
            disruption_files = resolve_disruptions(condition)
            result = await run_single(
                model_key=model_key,
                task=task,
                condition=condition,
                disruption_files=disruption_files or None,
                output_dir=run_output_dir,
                max_turns=max_turns,
                headless=headless,
                force_screenshot=force_screenshot,
            )
            all_results.append(result)
        return all_results, run_output_dir

    # Parallel mode — semaphore-gated, failure-isolated
    semaphore = asyncio.Semaphore(parallel)
    completed = 0

    async def run_guarded(job_idx: int, task: dict, model_key: str, condition: str):
        nonlocal completed
        async with semaphore:
            tag = f"{task['id']}/{model_key}/{condition}"
            logger.info(f"[{job_idx}/{len(jobs)}] Starting {tag}")
            try:
                disruption_files = resolve_disruptions(condition)
                result = await run_single(
                    model_key=model_key,
                    task=task,
                    condition=condition,
                    disruption_files=disruption_files or None,
                    output_dir=run_output_dir,
                    max_turns=max_turns,
                    headless=headless,
                    force_screenshot=force_screenshot,
                )
                completed += 1
                logger.info(f"[{completed}/{len(jobs)}] Completed {tag}")
                return result
            except Exception:
                completed += 1
                logger.exception(f"[{completed}/{len(jobs)}] Failed {tag}")
                return None

    pending = [
        asyncio.create_task(run_guarded(i, task, model_key, condition))
        for i, (task, model_key, condition) in enumerate(jobs, 1)
    ]

    all_results = []
    for coro in asyncio.as_completed(pending):
        result = await coro
        if result is not None:
            all_results.append(result)

    failed = len(jobs) - len(all_results)
    if failed:
        logger.warning(f"{failed}/{len(jobs)} tasks failed")

    return all_results, run_output_dir


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Browser Brawl Runner")
    parser.add_argument("--models", nargs="*", default=None, help="Models to test (default: all)")
    parser.add_argument("--tasks-file", default="tasks/amazon_selected.jsonl")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--max-turns", type=int, default=25)
    parser.add_argument("--headless", action="store_true", help="Run browser headless (default: headed)")
    parser.add_argument("--task-ids", nargs="*", default=None, help="Task IDs to run (default: all)")
    valid_conditions = list(DISRUPTION_SETS.keys())
    parser.add_argument("--conditions", nargs="*", default=None, choices=valid_conditions,
                        help=f"Conditions: {', '.join(valid_conditions)} (default: baseline)")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation after benchmark")
    parser.add_argument("--eval-model", default="gpt-4o")
    parser.add_argument("--force-screenshot", action="store_true",
                        help="Inject browser screenshots into the LLM context each turn")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Max concurrent browser tasks (default: 1, sequential)")
    args = parser.parse_args()

    if args.parallel > 1:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )

    # Run benchmark
    _results, run_output_dir = await run_benchmark(
        models=args.models,
        tasks_file=args.tasks_file,
        output_dir=args.output_dir,
        max_turns=args.max_turns,
        headless=args.headless,
        conditions=args.conditions,
        task_ids=args.task_ids,
        force_screenshot=args.force_screenshot,
        parallel=args.parallel,
    )

    # Optionally evaluate
    if args.evaluate:
        from openai import OpenAI
        from evaluator import summarize_results
        print(f"\n{'='*60}")
        print("RUNNING EVALUATION")
        print(f"{'='*60}")
        client = OpenAI()
        results = evaluate_results_dir(run_output_dir, args.tasks_file, client, args.eval_model)
        summarize_results(results, output_path=str(Path(run_output_dir) / "summary.json"))


if __name__ == "__main__":
    asyncio.run(main())
