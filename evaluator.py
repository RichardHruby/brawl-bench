"""
Browser Brawl — Evaluator

GPT-4V-based judge adapted from WebVoyager's auto_eval.py.
Text-based evaluation: task + agent answer → SUCCESS/NOT SUCCESS.
"""

import json
import re
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI


EVAL_SYSTEM_PROMPT = """You are an evaluator for a web browsing agent benchmark.

You will be given:
1. A web task instruction (what the agent was asked to do)
2. The agent's final response

Your job is to determine if the agent successfully completed the task.

Guidelines:
- The agent should have found specific, concrete information from the website
- Generic or hallucinated answers (not from the actual website) should be NOT SUCCESS
- If the task asks to find a product, the answer should include a specific product name/details
- If the agent says it couldn't find the information or encountered errors, that's NOT SUCCESS
- Partial completion (e.g., found a product but didn't check all filters) may be SUCCESS if the core task is done

Provide your reasoning, then end with exactly one of:
SUCCESS
NOT SUCCESS"""

EVAL_USER_PROMPT = """TASK: {task}

AGENT'S RESPONSE:
{answer}

Evaluate whether the agent successfully completed the task. Provide reasoning then your verdict."""


def extract_answer(final_output: str) -> str | None:
    """Extract answer from agent output using ANSWER; pattern."""
    if not final_output:
        return None
    # Try WebVoyager format first
    pattern = r"ANSWER[;: ]+\[?(.[^\]]*)\]?"
    match = re.search(pattern, final_output, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Return None if no ANSWER pattern found — agent must format answer properly
    return None


def evaluate_run(task_description: str, agent_output: str, client: OpenAI = None, model: str = "gpt-4o") -> dict:
    """
    Evaluate a single run using GPT-4V as judge.

    Returns:
        dict with keys: success (bool|None), reasoning (str), raw_response (str)
    """
    if client is None:
        client = OpenAI()

    answer = extract_answer(agent_output)
    if not answer:
        return {
            "success": False,
            "reasoning": "No answer provided by agent",
            "raw_response": "",
        }

    messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": EVAL_USER_PROMPT.format(task=task_description, answer=answer)},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1000,
        temperature=0,
    )

    raw = response.choices[0].message.content
    success = None
    if "NOT SUCCESS" in raw:
        success = False
    elif "SUCCESS" in raw:
        success = True

    return {
        "success": success,
        "reasoning": raw,
        "raw_response": raw,
    }


def evaluate_results_dir(results_dir: str, tasks_file: str, client: OpenAI = None, model: str = "gpt-4o") -> list[dict]:
    """Evaluate all runs in a results directory."""
    from pathlib import Path
    import os

    if client is None:
        client = OpenAI()

    # Load task descriptions
    tasks_by_id = {}
    with open(tasks_file) as f:
        for line in f:
            task = json.loads(line.strip())
            tasks_by_id[task["id"]] = task

    results = []
    results_path = Path(results_dir)

    for condition_dir in sorted(results_path.iterdir()):
        if not condition_dir.is_dir():
            continue
        condition = condition_dir.name

        for model_dir in sorted(condition_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            model_key = model_dir.name

            for task_dir in sorted(model_dir.iterdir()):
                if not task_dir.is_dir():
                    continue
                task_id = task_dir.name

                run_file = task_dir / "run.json"
                if not run_file.exists():
                    continue

                with open(run_file) as f:
                    run_data = json.load(f)

                task = tasks_by_id.get(task_id)
                if not task:
                    print(f"  Warning: no task found for {task_id}")
                    continue

                print(f"  Evaluating {condition}/{model_key}/{task_id}...")
                eval_result = evaluate_run(
                    task_description=task["ques"],
                    agent_output=run_data.get("final_output", ""),
                    client=client,
                    model=model,
                )

                result = {
                    "task_id": task_id,
                    "model_key": model_key,
                    "condition": condition,
                    "success": eval_result["success"],
                    "reasoning": eval_result["reasoning"],
                    "turns": run_data.get("turns", 0),
                    "elapsed_sec": run_data.get("elapsed_sec", 0),
                    "error": run_data.get("error"),
                    "answer": extract_answer(run_data.get("final_output", "")),
                }
                results.append(result)

                # Save eval result alongside run
                with open(task_dir / "eval.json", "w") as f:
                    json.dump(eval_result, f, indent=2)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate Browser Brawl results")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--tasks-file", default="tasks/amazon_selected.jsonl")
    parser.add_argument("--eval-model", default="gpt-4o")
    args = parser.parse_args()

    client = OpenAI()
    results = evaluate_results_dir(args.results_dir, args.tasks_file, client, args.eval_model)

    print(f"\n{'='*60}")
    print("EVALUATION RESULTS")
    print(f"{'='*60}")
    for r in results:
        status = "SUCCESS" if r["success"] else "FAIL" if r["success"] is False else "UNKNOWN"
        print(f"  {r['condition']:10s} | {r['model_key']:20s} | {r['task_id']:12s} | {status}")
