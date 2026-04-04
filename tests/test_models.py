from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import Observation, SecurityAuditAction, TriageAction, parse_action_union


def test_1_valid_observation_model_validate_succeeds() -> None:
    payload = {
        "task_id": "task_triage",
        "scenario_id": "triage-001",
        "context": "Incoming ticket about login failures",
        "available_actions": ["triage"],
        "step_number": 0,
        "episode_id": "ep-123",
    }

    obs = Observation.model_validate(payload)

    assert obs.task_id == "task_triage"
    assert obs.step_number == 0


def test_2_invalid_step_number_type_raises_validation_error() -> None:
    payload = {
        "task_id": "task_triage",
        "scenario_id": "triage-001",
        "context": "Incoming ticket about login failures",
        "available_actions": ["triage"],
        "step_number": "abc",
        "episode_id": "ep-123",
    }

    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_3_missing_required_field_raises_validation_error() -> None:
    payload = {
        "task_id": "task_triage",
        "scenario_id": "triage-001",
        "context": "Incoming ticket about login failures",
        "available_actions": ["triage"],
        "step_number": 0,
    }

    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_4_action_union_discriminates_triage_and_security() -> None:
    triage_payload = {
        "category": "bug",
        "severity": "high",
        "module_label": "auth",
        "oncall_routing": "backend-oncall",
    }
    security_payload = {
        "findings": [
            {
                "cwe_id": "CWE-79",
                "line_number": 42,
                "severity": "high",
                "fix_description": "Escape user input",
            }
        ]
    }

    triage_action = parse_action_union(triage_payload)
    security_action = parse_action_union(security_payload)

    assert isinstance(triage_action, TriageAction)
    assert isinstance(security_action, SecurityAuditAction)


def test_5_observation_dump_round_trip() -> None:
    original = Observation.model_validate(
        {
            "task_id": "task_dependency_update",
            "scenario_id": "dep-001",
            "context": "Upgrade urllib3",
            "available_actions": ["dependency_update"],
            "step_number": 0,
            "episode_id": "ep-456",
        }
    )

    dumped = original.model_dump()
    reloaded = Observation.model_validate(dumped)

    assert reloaded == original
