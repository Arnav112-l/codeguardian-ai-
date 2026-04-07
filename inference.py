#!/usr/bin/env python3
"""
CodeGuardian AI - Inference Script for OpenEnv Hackathon Submission

This script runs all 15 scenarios (5 triage, 5 security, 5 dependency) using
OpenAI-compatible API via HuggingFace router.

Required Environment Variables:
    API_BASE_URL: API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME: Model to use (default: Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN: HuggingFace API token (required for live runs)
    OPENENV_URL: OpenEnv grading server (default: https://zeus1205-codeguardian-ai.hf.space)

Output Format (mandatory for hackathon):
    [START] task=<task_name> env=codeguardian model=<MODEL_NAME>
    [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<null|msg>
    [END] success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import httpx

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment, misc]

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
OPENENV_URL = os.getenv("OPENENV_URL", "https://zeus1205-codeguardian-ai.hf.space")

# Scenario definitions: 15 total (5 per task type)
SCENARIOS = {
    "triage": [f"triage-{i:03d}" for i in range(1, 6)],
    "security": [f"security-{i:03d}" for i in range(1, 6)],
    "dependency": [f"dependency-{i:03d}" for i in range(1, 6)],
}

# System prompts for each task type
SYSTEM_PROMPTS = {
    "triage": (
        'You are a support ticket triage agent. Analyze the ticket and respond ONLY with valid JSON.\n'
        'Required format: {"category": "...", "severity": "...", "assignee": "...", "decision": "..."}\n\n'
        'CATEGORY: "bug", "feature", "docs", or "question"\n'
        'SEVERITY: "critical", "high", "medium", or "low"\n'
        'ASSIGNEE: team routing like "backend-oncall", "payments-oncall", "support-oncall"\n'
        'DECISION: "continue" or "stop"'
    ),
    "security": (
        'You are a security auditor. Identify vulnerabilities and respond ONLY with valid JSON.\n'
        'Required format: {"findings": [{"cwe_id": "CWE-XXX", "line_number": N, "severity": "...", "fix_description": "..."}]}\n\n'
        'Common CWEs: CWE-79 (XSS), CWE-89 (SQLi), CWE-502 (Deserialization), CWE-330 (Weak Random)\n'
        'SEVERITY: "low", "medium", "high", or "critical"'
    ),
    "dependency": (
        'You are a dependency upgrade advisor. Respond ONLY with valid JSON.\n'
        'Required format: {"updates": [{"package": "...", "from_version": "...", "to_version": "...", "is_breaking": true/false, "migration_notes": "..."}]}\n\n'
        'Recommend appropriate modern versions with migration guidance.'
    ),
}


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]  # Remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove closing fence
        cleaned = "\n".join(lines).strip()
    if cleaned.lower().startswith("json\n"):
        cleaned = cleaned[5:].strip()
    return cleaned


def call_openenv_reset(base_url: str) -> dict[str, Any]:
    """POST /reset to initialize environment."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{base_url}/reset")
        resp.raise_for_status()
        return resp.json()


def call_openenv_step(base_url: str, action_type: str, scenario_id: str, payload: dict) -> dict[str, Any]:
    """POST /step with action payload."""
    body = {
        "action_type": action_type,
        "scenario_id": scenario_id,
        "payload": payload,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{base_url}/step", json=body)
        resp.raise_for_status()
        return resp.json()


def get_scenario_context(base_url: str, scenario_id: str) -> str:
    """Get scenario context from /scenarios endpoint."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{base_url}/scenarios")
        resp.raise_for_status()
        scenarios = resp.json()
        if isinstance(scenarios, dict) and "scenarios" in scenarios:
            scenarios = scenarios["scenarios"]
        for s in scenarios:
            if s.get("id") == scenario_id:
                return s.get("context", s.get("description", ""))
        return ""


def call_llm(client: Any, task_type: str, context: str) -> dict[str, Any]:
    """Call LLM to generate action payload."""
    user_prompt = f"Context:\n{context}\n\nRespond with the required JSON format only."
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPTS[task_type]},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=1024,
    )
    
    raw = response.choices[0].message.content or "{}"
    cleaned = strip_code_fences(raw)
    return json.loads(cleaned)


def run_episode(
    llm_client: Any,
    task_type: str,
    scenario_id: str,
    mock: bool = False,
) -> tuple[float, list[float], bool, str | None]:
    """
    Run a single episode for one scenario.
    
    Returns: (total_score, rewards_list, success, error_message)
    """
    rewards: list[float] = []
    error_msg: str | None = None
    total_score = 0.0
    success = False
    
    # Print [START] log
    print(f"[START] task={task_type} env=codeguardian model={MODEL_NAME}")
    
    try:
        # Get scenario context
        context = get_scenario_context(OPENENV_URL, scenario_id)
        
        # Generate action using LLM or mock
        if mock:
            if task_type == "triage":
                payload = {"category": "bug", "severity": "high", "assignee": "backend-oncall", "decision": "continue"}
            elif task_type == "security":
                payload = {"findings": [{"cwe_id": "CWE-89", "line_number": 10, "severity": "high", "fix_description": "Use parameterized queries"}]}
            else:
                payload = {"updates": [{"package": "requests", "from_version": "2.25.0", "to_version": "2.32.3", "is_breaking": False, "migration_notes": "Update to latest stable version"}]}
        else:
            payload = call_llm(llm_client, task_type, context)
        
        # Submit action to OpenEnv
        result = call_openenv_step(OPENENV_URL, task_type, scenario_id, payload)
        
        # Extract score
        total_score = result.get("total_score", 0.0)
        rewards.append(total_score)
        done = result.get("done", True)
        
        # Print [STEP] log
        action_str = json.dumps(payload, separators=(",", ":"))
        print(f"[STEP] step=1 action={action_str} reward={total_score:.2f} done={'true' if done else 'false'} error=null")
        
        success = True
        
    except Exception as e:
        error_msg = str(e).replace("\n", " ")[:100]
        print(f"[STEP] step=1 action={{}} reward=0.00 done=true error={error_msg}")
        rewards.append(0.0)
    
    # Print [END] log
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={'true' if success else 'false'} steps={len(rewards)} score={total_score:.2f} rewards={rewards_str}")
    
    return total_score, rewards, success, error_msg


def run(mock: bool = False) -> int:
    """Run all 15 scenarios and output results."""
    
    # Validate environment
    if not mock:
        if OpenAI is None:
            print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
            return 1
        if not HF_TOKEN:
            print("ERROR: HF_TOKEN environment variable required", file=sys.stderr)
            return 1
    
    # Initialize OpenAI client
    llm_client = None
    if not mock:
        llm_client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)
    
    # Reset environment
    print(f"Initializing OpenEnv at {OPENENV_URL}...")
    try:
        reset_result = call_openenv_reset(OPENENV_URL)
        print(f"Reset complete: {reset_result.get('total_scenarios', 15)} scenarios loaded")
    except Exception as e:
        print(f"ERROR: Failed to reset environment: {e}", file=sys.stderr)
        return 1
    
    # Track results
    all_scores: dict[str, list[float]] = {"triage": [], "security": [], "dependency": []}
    total_success = 0
    total_episodes = 0
    start_time = time.time()
    
    # Run all 15 scenarios
    for task_type, scenario_ids in SCENARIOS.items():
        for scenario_id in scenario_ids:
            total_episodes += 1
            print(f"\n{'='*60}")
            print(f"Episode {total_episodes}/15: {scenario_id}")
            print(f"{'='*60}")
            
            score, rewards, success, error = run_episode(
                llm_client=llm_client,
                task_type=task_type,
                scenario_id=scenario_id,
                mock=mock,
            )
            
            all_scores[task_type].append(score)
            if success:
                total_success += 1
    
    # Print summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total episodes: {total_episodes}")
    print(f"Successful: {total_success}")
    print(f"Failed: {total_episodes - total_success}")
    print(f"Runtime: {elapsed:.1f}s")
    print()
    print("Scores by task:")
    print("-" * 40)
    for task_type, scores in all_scores.items():
        avg = sum(scores) / len(scores) if scores else 0.0
        print(f"  {task_type:12s}: {avg:.2f} avg ({len(scores)} scenarios)")
    
    overall_avg = sum(sum(s) for s in all_scores.values()) / total_episodes if total_episodes else 0.0
    print(f"\nOverall average: {overall_avg:.2f}")
    
    # Write results to file
    with open("results.jsonl", "w") as f:
        for task_type, scores in all_scores.items():
            for i, score in enumerate(scores):
                record = {
                    "task_type": task_type,
                    "scenario_id": SCENARIOS[task_type][i],
                    "score": score,
                    "model": MODEL_NAME,
                }
                f.write(json.dumps(record) + "\n")
    
    print(f"\nResults saved to results.jsonl")
    
    return 0 if total_success == total_episodes else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="CodeGuardian AI - Run OpenEnv evaluation across all 15 scenarios"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with mock actions (no LLM calls)",
    )
    args = parser.parse_args(argv)
    return run(mock=args.mock)


if __name__ == "__main__":
    raise SystemExit(main())
