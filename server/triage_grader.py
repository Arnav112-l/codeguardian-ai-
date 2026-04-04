"""
OptiMaintainer — Issue Triage Grader (Easy Track)

Scoring dimensions:
  • category_score  — 1.0 for exact match, 0.0 otherwise
  • severity_score  — based on ordinal distance (low=0 … critical=3)
  • routing_score   — 1.0 exact assignee, 0.5 correct domain, 0.0 wrong
  • decision_score  — 1.0 for correct STOP/CONTINUE decision
"""

from __future__ import annotations

from typing import Any, Dict, List

from models import (
    Action,
    Observation,
    Severity,
    SubScore,
    TriageActionPayload,
    TriageDecision,
)

# Ordinal mapping for severity distance calculation
_SEVERITY_ORD: Dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

# Routing rules: assignee → expected decision
_ROUTING_RULES: Dict[str, TriageDecision] = {
    "oncall:distributed": TriageDecision.STOP,
    "oncall:pt2": TriageDecision.CONTINUE,
}


def _category_score(predicted: str, expected: str) -> SubScore:
    hit = predicted.strip().lower() == expected.strip().lower()
    return SubScore(
        name="category",
        score=1.0 if hit else 0.0,
        feedback=(
            f"Correct category: '{expected}'"
            if hit
            else f"Expected category '{expected}', got '{predicted}'"
        ),
    )


def _severity_score(predicted: Severity, expected: Severity) -> SubScore:
    p_ord = _SEVERITY_ORD[predicted.value]
    e_ord = _SEVERITY_ORD[expected.value]
    diff = abs(p_ord - e_ord)

    if diff == 0:
        score, msg = 1.0, f"Exact severity match: {expected.value}"
    elif diff == 1:
        score, msg = 0.5, f"Severity one level off (expected {expected.value}, got {predicted.value})"
    else:
        score, msg = 0.0, f"Severity too far off (expected {expected.value}, got {predicted.value}, distance={diff})"

    return SubScore(name="severity", score=score, feedback=msg)


def _routing_score(predicted: str, expected_assignee: str, expected_domain: str) -> SubScore:
    pred = predicted.strip().lower()
    exp_assignee = expected_assignee.strip().lower()
    exp_domain = expected_domain.strip().lower()

    if pred == exp_assignee:
        return SubScore(name="routing", score=1.0, feedback=f"Exact assignee match: {expected_assignee}")

    # Check if the predicted assignee is in the correct domain
    if exp_domain and pred.startswith(exp_domain):
        return SubScore(
            name="routing",
            score=0.5,
            feedback=f"Correct domain '{exp_domain}' but wrong specific assignee (expected {expected_assignee})",
        )

    return SubScore(
        name="routing",
        score=0.0,
        feedback=f"Wrong routing: expected '{expected_assignee}', got '{pred}'",
    )


def _decision_score(predicted: TriageDecision, expected: TriageDecision) -> SubScore:
    hit = predicted == expected
    return SubScore(
        name="decision",
        score=1.0 if hit else 0.0,
        feedback=(
            f"Correct decision: {expected.value}"
            if hit
            else f"Expected decision '{expected.value}', got '{predicted.value}'"
        ),
    )


def grade(action: Action, reference: Dict[str, Any]) -> Observation:
    """
    Grade a triage action against the reference answer from scenario_bank.

    Parameters
    ----------
    action : Action
        The agent's submitted triage action.
    reference : dict
        Expected answer with keys: category, severity, assignee, domain, decision.

    Returns
    -------
    Observation with sub_scores and total_score (simple average of 4 dimensions).
    """
    payload = action.parse_triage()

    sub_scores: List[SubScore] = [
        _category_score(payload.category, reference["category"]),
        _severity_score(payload.severity, Severity(reference["severity"])),
        _routing_score(
            payload.assignee,
            reference["assignee"],
            reference.get("domain", ""),
        ),
        _decision_score(
            payload.decision,
            TriageDecision(reference["decision"]),
        ),
    ]

    total = sum(s.score for s in sub_scores) / len(sub_scores)
    feedback_parts = [f"[{s.name}] {s.feedback}" for s in sub_scores]

    return Observation(
        scenario_id=action.scenario_id,
        action_type=action.action_type,
        total_score=round(total, 4),
        sub_scores=sub_scores,
        feedback=" | ".join(feedback_parts),
    )
