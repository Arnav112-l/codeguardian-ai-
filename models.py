"""
OptiMaintainer — Pydantic models for the OpenEnv grading environment.

Defines the core Action (agent → env) and Observation (env → agent) schemas
used by all three grading tracks: Triage, Security, and Dependency.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────
#  Enumerations
# ─────────────────────────────────────────────

class ActionType(str, Enum):
    TRIAGE = "triage"
    SECURITY = "security"
    DEPENDENCY = "dependency"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TriageDecision(str, Enum):
    STOP = "stop"
    CONTINUE = "continue"


# ─────────────────────────────────────────────
#  Action payloads (agent → environment)
# ─────────────────────────────────────────────

class TriageActionPayload(BaseModel):
    """Payload for issue-triage actions."""
    category: str = Field(..., description="Predicted issue category (e.g. 'bug', 'feature', 'performance')")
    severity: Severity = Field(..., description="Predicted severity level")
    assignee: str = Field(..., description="Oncall or person to route the issue to")
    decision: TriageDecision = Field(..., description="STOP or CONTINUE escalation")


class SecurityFinding(BaseModel):
    """A single vulnerability finding reported by the agent."""
    cwe_id: str = Field(..., description="CWE identifier, e.g. 'CWE-89'")
    line_number: int = Field(..., ge=1, description="Source line where the vuln was found")
    fix_description: str = Field("", description="Short description of the recommended fix")


class SecurityActionPayload(BaseModel):
    """Payload for security-audit actions."""
    findings: List[SecurityFinding] = Field(default_factory=list)


class DependencyUpdate(BaseModel):
    """A single dependency update proposed by the agent."""
    package: str = Field(..., description="Package name, e.g. 'requests'")
    from_version: str = Field(..., description="Current version string")
    to_version: str = Field(..., description="Target version string")
    is_breaking: bool = Field(False, description="Whether the update is breaking")
    migration_notes: str = Field("", description="Free-text migration instructions")


class DependencyActionPayload(BaseModel):
    """Payload for dependency-updater actions."""
    updates: List[DependencyUpdate] = Field(default_factory=list)


class Action(BaseModel):
    """
    Top-level action sent by an AI agent.

    The `action_type` discriminator selects which grader processes the payload.
    """
    action_type: ActionType
    scenario_id: str = Field(..., description="ID of the scenario being answered")
    payload: Dict[str, Any] = Field(..., description="Action-type-specific payload")

    def parse_triage(self) -> TriageActionPayload:
        return TriageActionPayload(**self.payload)

    def parse_security(self) -> SecurityActionPayload:
        return SecurityActionPayload(**self.payload)

    def parse_dependency(self) -> DependencyActionPayload:
        return DependencyActionPayload(**self.payload)


# ─────────────────────────────────────────────
#  Observation (environment → agent)
# ─────────────────────────────────────────────

class SubScore(BaseModel):
    """An individual grading dimension."""
    name: str
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str = ""


class Observation(BaseModel):
    """
    Response returned to the agent after each /step call.
    """
    scenario_id: str
    action_type: ActionType
    total_score: float = Field(..., ge=0.0, le=1.0)
    sub_scores: List[SubScore] = Field(default_factory=list)
    feedback: str = Field("", description="Human-readable explanation of the grade")
    done: bool = Field(False, description="Whether the episode is complete")


# ─────────────────────────────────────────────
#  Environment state
# ─────────────────────────────────────────────

class EnvState(BaseModel):
    """Tracks the current episode state across /reset and /step calls."""
    current_scenario_idx: int = 0
    completed_scenarios: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)
    episode_done: bool = False
