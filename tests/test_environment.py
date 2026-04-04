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


def test_integration_1_ground_truth_agent_achieves_score_gte_0_9() -> None:
    env = CodingEnvironment()
    all_scores: list[float] = []

    for task_id, scenarios in SCENARIO_BANK.items():
        for scenario_index, scenario in enumerate(scenarios):
            env.reset(task_id, scenario_index)
            action = _ground_truth_action(task_id, scenario)
            _, reward, done, _ = env.step(action)
            assert done is True
            all_scores.append(reward.total_score)

    average_score = sum(all_scores) / len(all_scores)
    assert average_score >= 0.9


def test_integration_2_bad_action_scores_near_zero() -> None:
    env = CodingEnvironment()
    all_scores: list[float] = []

    for task_id, scenarios in SCENARIO_BANK.items():
        for scenario_index, _ in enumerate(scenarios):
            env.reset(task_id, scenario_index)
            action = _bad_action(task_id)
            _, reward, done, _ = env.step(action)
            assert done is True
            all_scores.append(reward.total_score)

    average_score = sum(all_scores) / len(all_scores)
    assert average_score <= 0.2


def test_integration_3_reset_twice_no_state_bleed_between_episodes() -> None:
    env = CodingEnvironment()

    first_obs = env.reset("task_triage", 0)
    first_action = _ground_truth_action("task_triage", SCENARIO_BANK["task_triage"][0])
    env.step(first_action)

    second_obs = env.reset("task_security_audit", 1)
    current_state = env.state()

    assert first_obs.episode_id != second_obs.episode_id
    assert second_obs.step_number == 0
    assert current_state.task_id == "task_security_audit"
    assert current_state.step_count == 0
    assert current_state.cumulative_reward == 0.0


def test_no_ground_truth_leak() -> None:
    env = CodingEnvironment()
    obs = env.reset("task_dependency_update", 0)

    dumped = obs.model_dump()
    assert "ground_truth" not in dumped
    assert "ground_truth" not in obs.__dict__
