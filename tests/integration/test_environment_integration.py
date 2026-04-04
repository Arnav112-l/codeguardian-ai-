from __future__ import annotations

from environment import CodingEnvironment
from models import DependencyAction, SecurityAuditAction, TriageAction
from scenario_bank import SCENARIO_BANK


def _ground_truth_action(task_id: str, scenario: dict) -> object:
    ground_truth = scenario["ground_truth"]
    if task_id == "task_triage":
        return TriageAction.model_validate(ground_truth)
    if task_id == "task_security_audit":
        return SecurityAuditAction.model_validate(ground_truth)
    return DependencyAction.model_validate(ground_truth)


def _bad_action(task_id: str) -> object:
    if task_id == "task_triage":
        return TriageAction.model_validate(
            {
                "category": "docs",
                "severity": "low",
                "module_label": "unknown-module",
                "oncall_routing": "nobody",
            }
        )
    if task_id == "task_security_audit":
        return SecurityAuditAction.model_validate(
            {
                "findings": [
                    {
                        "cwe_id": "CWE-000",
                        "line_number": 1,
                        "severity": "low",
                        "fix_description": "No-op",
                    }
                ]
            }
        )
    return DependencyAction.model_validate(
        {
            "updated_version": "package==0.0.1",
            "breaking_changes": [],
            "migration_description": "",
        }
    )


def test_ground_truth_agent_scores_high() -> None:
    env = CodingEnvironment()
    scores: list[float] = []

    for task_id, scenarios in SCENARIO_BANK.items():
        for scenario_index, scenario in enumerate(scenarios):
            env.reset(task_id, scenario_index)
            action = _ground_truth_action(task_id, scenario)
            _, reward, _, _ = env.step(action)
            scores.append(reward.total_score)

    assert (sum(scores) / len(scores)) >= 0.9


def test_bad_actions_score_low() -> None:
    env = CodingEnvironment()
    scores: list[float] = []

    for task_id, scenarios in SCENARIO_BANK.items():
        for scenario_index, _ in enumerate(scenarios):
            env.reset(task_id, scenario_index)
            action = _bad_action(task_id)
            _, reward, _, _ = env.step(action)
            scores.append(reward.total_score)

    assert (sum(scores) / len(scores)) <= 0.2


def test_reset_has_no_state_bleed() -> None:
    env = CodingEnvironment()

    first = env.reset("task_triage", 0)
    env.step(_ground_truth_action("task_triage", SCENARIO_BANK["task_triage"][0]))
    second = env.reset("task_dependency_update", 0)
    state = env.state()

    assert first.episode_id != second.episode_id
    assert state.step_count == 0
    assert state.cumulative_reward == 0.0
