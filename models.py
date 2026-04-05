from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Literal, Union
from pydantic import BaseModel, ConfigDict, TypeAdapter

class ActionType(str, Enum):
    TRIAGE = "triage"
    SECURITY = "security"
    DEPENDENCY = "dependency"

class EnvState(BaseModel):
    completed_scenarios: List[str] = []
    scores: Dict[str, float] = {}
    episode_done: bool = False
    current_scenario_idx: int = 0

class Observation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    task_id: str | None = None
    scenario_id: str
    context: Any | None = None
    available_actions: List[str] | None = None
    step_number: int | None = None
    episode_id: str | None = None
    
    # Grading results (optional for initial reset)
    action_type: str | None = None
    total_score: float | None = None
    sub_scores: List[Dict[str, Any]] | None = None
    feedback: str | None = None
    done: bool = False


class TriageAction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    category: Literal["bug", "feature", "documentation", "performance", "docs", "question"]
    severity: Literal["low", "medium", "high", "critical"]
    assignee: str
    decision: Literal["stop", "continue"]


class Finding(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    cwe_id: str
    line_number: int
    severity: str
    fix_description: str


class SecurityAuditAction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    findings: List[Finding]


class DependencyUpdate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    package: str
    from_version: str
    to_version: str
    is_breaking: bool
    migration_notes: str


class DependencyAction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    updates: List[DependencyUpdate]


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
    task_norm = task_id.lower().replace("task_", "").replace("_update", "").replace("_audit", "")
    model_by_task = {
        "triage": TriageAction,
        "security": SecurityAuditAction,
        "dependency": DependencyAction,
    }
    action_model = model_by_task.get(task_norm)
    if action_model is None:
        raise ValueError(f"Unknown task_id for action validation: {task_id} (norm={task_norm})")
    return action_model.model_validate(payload)
