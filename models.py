from __future__ import annotations

from typing import Any, Dict, List, Literal, Union

from pydantic import BaseModel, ConfigDict, TypeAdapter


class Observation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task_id: str
    scenario_id: str
    context: str
    available_actions: list[str]
    step_number: int
    episode_id: str


class TriageAction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    category: Literal["bug", "feature", "docs", "question"]
    severity: Literal["low", "medium", "high", "critical"]
    module_label: str
    oncall_routing: str


class Finding(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    cwe_id: str
    line_number: int
    severity: str
    fix_description: str


class SecurityAuditAction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    findings: List[Finding]


class DependencyAction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    updated_version: str
    breaking_changes: List[str]
    migration_description: str


Action = Union[TriageAction, SecurityAuditAction, DependencyAction]
ACTION_ADAPTER = TypeAdapter(Action)


class Reward(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    total_score: float
    sub_scores: Dict[str, float]
    feedback: str
    is_terminal: bool


class State(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    episode_id: str
    task_id: str
    step_count: int
    current_scenario_id: str
    cumulative_reward: float


def parse_action_union(payload: Dict[str, Any]) -> Action:
    """Validate an action payload through the Action union adapter."""
    return ACTION_ADAPTER.validate_python(payload)


def model_validate_action(payload: Dict[str, Any], task_id: str) -> Action:
    """Validate payload against the task-specific action model."""
    model_by_task = {
        "task_triage": TriageAction,
        "task_security_audit": SecurityAuditAction,
        "task_dependency_update": DependencyAction,
        "task_dependency": DependencyAction,
    }
    action_model = model_by_task.get(task_id)
    if action_model is None:
        raise ValueError(f"Unknown task_id for action validation: {task_id}")
    return action_model.model_validate(payload)
