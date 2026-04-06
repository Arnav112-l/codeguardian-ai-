from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from typing import Any

from environment import CodingEnvironment
from models import Action, DependencyAction, SecurityAuditAction, TriageAction, model_validate_action

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - handled at runtime for mock-only workflows
    OpenAI = None  # type: ignore[assignment]


TASKS = ["task_triage", "task_security_audit", "task_dependency_update"]
TARGET_SCORES = {
    "task_triage": 0.75,
    "task_security_audit": 0.55,
    "task_dependency_update": 0.35,
}

SYSTEM_PROMPTS = {
    "task_triage": (
        'You are a support ticket triage agent. Analyze the ticket carefully and respond ONLY with valid JSON.\n'
        'Required format: {"category": "...", "severity": "...", "module_label": "...", "oncall_routing": "..."}\n\n'
        'CATEGORY (choose exactly one):\n'
        '- "bug": system errors, crashes, failures, things not working as expected\n'
        '- "feature": new functionality requests, enhancements, product asks\n'
        '- "docs": documentation issues, missing guides, unclear instructions\n'
        '- "question": user asking for information, clarification, how things work\n\n'
        'SEVERITY (choose exactly one):\n'
        '- "critical": data loss, security breach, complete outage, double charging\n'
        '- "high": major functionality broken, significant user impact\n'
        '- "medium": partial functionality affected, workaround exists\n'
        '- "low": minor issues, cosmetic, nice-to-have\n\n'
        'module_label: extract the specific service/module name mentioned (e.g., "auth-service", "payment-gateway", "analytics-ui")\n'
        'oncall_routing: route to appropriate team based on module (e.g., "backend-oncall", "payments-oncall", "support-oncall", "devrel-oncall", "product-oncall")'
    ),
    "task_security_audit": (
        'You are a security auditor. Identify vulnerabilities and respond ONLY with valid JSON.\n'
        'Required format: {"findings": [{"cwe_id": "CWE-XXX", "line_number": N, "severity": "...", "fix_description": "..."}]}\n\n'
        'Common CWE IDs:\n'
        '- CWE-79: Cross-site Scripting (XSS) - unescaped HTML output\n'
        '- CWE-89: SQL Injection - string concatenation in queries\n'
        '- CWE-502: Deserialization of Untrusted Data - pickle/yaml.load\n'
        '- CWE-330: Insufficient Randomness - random.random() for security\n'
        '- CWE-862: Missing Authorization - no role/permission checks\n\n'
        'line_number: integer line number where the vulnerability exists\n'
        'severity: "low", "medium", "high", or "critical"\n'
        'fix_description: specific remediation steps'
    ),
    "task_dependency_update": (
        'You are a dependency upgrade advisor. Analyze the current dependency issue and respond ONLY with valid JSON.\n'
        'Required format: {"updated_version": "package==X.Y.Z", "breaking_changes": ["change1", "change2"], "migration_description": "..."}\n\n'
        'IMPORTANT GUIDELINES:\n'
        '- updated_version: Use format "packagename==X.Y.Z" with a recent stable version\n'
        '  Examples: "requests==2.32.3", "pydantic==2.12.5", "openai==2.30.0", "pytest==9.0.2", "httpx==0.28.1"\n'
        '- breaking_changes: List specific API/behavior changes developers must address (at least 2 items)\n'
        '- migration_description: Write a detailed migration plan with specific steps (must be at least 20 characters)\n\n'
        'Focus on the EXACT package mentioned in the context and recommend appropriate modern version.'
    ),
}


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    if cleaned.lower().startswith("json\n"):
        cleaned = cleaned[5:].strip()
    return cleaned


def _build_user_prompt(obs: Any) -> str:
    return (
        f"Task: {obs.task_id}\n"
        f"Scenario: {obs.scenario_id}\n"
        f"Context:\n{obs.context}\n\n"
        f"Available actions: {obs.available_actions}\n"
        "Return only JSON matching the required schema."
    )


def _mock_action_for_task(task_id: str) -> Action:
    if task_id == "task_triage":
        return TriageAction.model_validate(
            {
                "category": random.choice(["bug", "feature", "documentation", "performance"]),
                "severity": random.choice(["low", "medium", "high", "critical"]),
                "assignee": random.choice(
                    ["oncall:distributed", "oncall:pt2", "oncall:serialization", "oncall:docs", "oncall:performance"]
                ),
                "decision": random.choice(["stop", "continue"]),
            }
        )
    if task_id == "task_security_audit":
        return SecurityAuditAction.model_validate(
            {
                "findings": [
                    {
                        "cwe_id": random.choice(
                            ["CWE-79", "CWE-89", "CWE-502", "CWE-22", "CWE-918"]
                        ),
                        "line_number": random.randint(1, 10),
                        "severity": random.choice(["low", "medium", "high", "critical"]),
                        "fix_description": "Use parameterized queries and sanitize user input.",
                    }
                ]
            }
        )
    return DependencyAction.model_validate(
        {
            "updates": [
                {
                    "package": random.choice(["numpy", "pydantic", "flask", "requests", "transformers"]),
                    "from_version": "1.0.0",
                    "to_version": random.choice(["2.0.0", "2.5.3", "3.0.0", "2.32.3", "4.40.0"]),
                    "is_breaking": random.choice([True, False]),
                    "migration_notes": "Update deprecated APIs, check compatibility, run tests.",
                }
            ]
        }
    )


def _call_llm_for_action(client: Any, model_name: str, task_id: str, obs: Any) -> tuple[Action, int]:
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPTS[task_id]},
            {"role": "user", "content": _build_user_prompt(obs)},
        ],
        temperature=0,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    raw = response.choices[0].message.content or ""
    clean = _strip_code_fences(raw)
    action_dict = json.loads(clean)
    action = model_validate_action(action_dict, task_id)
    return action, latency_ms


def _print_score_table(scores_by_task: dict[str, list[float]]) -> None:
    print("task                  | avg_score | target")
    print("----------------------|-----------|-------")
    for task_id in TASKS:
        scores = scores_by_task.get(task_id, [])
        avg_score = (sum(scores) / len(scores)) if scores else 0.0
        print(f"{task_id:<22}|   {avg_score:.2f}    |  {TARGET_SCORES[task_id]:.2f}")


def run(mock: bool) -> int:
    env = CodingEnvironment()
    results_path = "results.jsonl"

    model_name = os.getenv("MODEL_NAME", "mock-model" if mock else "")
    api_base_url = os.getenv("API_BASE_URL", "")
    hf_token = os.getenv("HF_TOKEN", "")

    client: Any = None
    if not mock:
        missing = [
            key
            for key, value in {
                "MODEL_NAME": model_name,
                "API_BASE_URL": api_base_url,
                "HF_TOKEN": hf_token,
            }.items()
            if not value
        ]
        if missing:
            print(
                f"Missing required environment variables for live run: {', '.join(missing)}",
                file=sys.stderr,
            )
            return 1

        if OpenAI is None:
            print("openai package is not available. Install requirements first.", file=sys.stderr)
            return 1

        client = OpenAI(base_url=api_base_url, api_key=hf_token)

    scores_by_task: dict[str, list[float]] = defaultdict(list)

    with open(results_path, "w", encoding="utf-8") as handle:
        for task_id in TASKS:
            for scenario_index in range(5):
                obs = env.reset(task_id, scenario_index)
                latency_ms = 0
                total_score = 0.0
                sub_scores: dict[str, float] = {}

                try:
                    if mock:
                        action = _mock_action_for_task(task_id)
                    else:
                        action, latency_ms = _call_llm_for_action(
                            client=client,
                            model_name=model_name,
                            task_id=task_id,
                            obs=obs,
                        )

                    _, reward, _, _ = env.step(action)
                    total_score = reward.total_score
                    sub_scores = reward.sub_scores
                except Exception as exc:
                    print(
                        (
                            "[WARN] Failed episode "
                            f"task={task_id} scenario={obs.scenario_id} "
                            f"episode={obs.episode_id}: {exc}"
                        ),
                        file=sys.stderr,
                    )

                scores_by_task[task_id].append(total_score)
                record = {
                    "episode_id": obs.episode_id,
                    "task_id": task_id,
                    "scenario_id": obs.scenario_id,
                    "model": model_name,
                    "total_score": total_score,
                    "sub_scores": sub_scores,
                    "latency_ms": latency_ms,
                }
                handle.write(json.dumps(record) + "\n")

    _print_score_table(scores_by_task)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run coding environment evaluation")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with synthetic actions and skip external API calls.",
    )
    args = parser.parse_args(argv)
    return run(mock=args.mock)


if __name__ == "__main__":
    raise SystemExit(main())
