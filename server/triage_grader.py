"""
OptiMaintainer — Issue Triage Grader (Easy Track)

Scoring dimensions:
  • category_score  — 1.0 for exact match, 0.0 otherwise
  • severity_score  — 1.0 exact, 0.5 for adjacency (±1), 0.0 otherwise
  • routing_score   — 1.0 exact assignee, 0.5 correct domain, 0.0 wrong
  • Total = (Category + Severity + Routing) / 3.0
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

def _category_score(predicted: str, expected: str) -> SubScore:
    hit = predicted.strip().lower() == expected.strip().lower()
    return SubScore(
        name="category",
        score=1.0 if hit else 0.0,
        feedback=(
            f"Correct category identified: '{expected}'"
            if hit
            else f"Category mismatch: expected '{expected}', found '{predicted}'"
        ),
    )


def _severity_score(predicted: Severity, expected: Severity) -> SubScore:
    p_ord = _SEVERITY_ORD.get(predicted.value.lower(), 0)
    e_ord = _SEVERITY_ORD.get(expected.value.lower(), 0)
    diff = abs(p_ord - e_ord)

    if diff == 0:
        score, msg = 1.0, f"Exact severity match: {expected.value}"
    elif diff == 1:
        score, msg = 0.5, f"Partial credit: severity '{predicted.value}' is adjacent to expected '{expected.value}'"
    else:
        score, msg = 0.0, f"Severity mismatch: expected '{expected.value}', got '{predicted.value}' (distance {diff})"

    return SubScore(name="severity", score=score, feedback=msg)


def _routing_score(predicted: str, expected_assignee: str, expected_domain: str) -> SubScore:
    pred = predicted.strip().lower()
    exp_assignee = expected_assignee.strip().lower()
    exp_domain = expected_domain.strip().lower()

    if pred == exp_assignee:
        return SubScore(name="routing", score=1.0, feedback=f"Correct routing to {expected_assignee}")

    if exp_domain and pred.startswith(exp_domain):
        return SubScore(
            name="routing",
            score=0.5,
            feedback=f"Correct domain '{exp_domain}' but wrong assignee (expected {expected_assignee})",
        )

    return SubScore(
        name="routing",
        score=0.0,
        feedback=f"Incorrect routing: expected '{expected_assignee}', got '{pred}'",
    )


def _decision_score(predicted: TriageDecision, expected: TriageDecision) -> SubScore:
    hit = predicted == expected
    return SubScore(
        name="decision",
        score=1.0 if hit else 0.0,
        feedback=(
            f"Correct decision: {expected.value}"
            if hit
            else f"Decision error: expected '{expected.value}', got '{predicted.value}'"
        ),
    )


def grade(action: Action, reference: Dict[str, Any]) -> Observation:
    """
    Grade a triage action against the reference answer.
    Formula: (cat_score + sev_score + routing_score) / 3.0
    """
    payload = action.parse_triage()

    cat = _category_score(payload.category, reference["category"])
    sev = _severity_score(payload.severity, Severity(reference["severity"]))
    rot = _routing_score(
        payload.assignee,
        reference["assignee"],
        reference.get("domain", ""),
    )
    dec = _decision_score(
        payload.decision,
        TriageDecision(reference["decision"]),
    )

    sub_scores = [cat, sev, rot, dec]
    
    # Per PDF spec: total is average of Cat, Sev, and Routing
    total = (cat.score + sev.score + rot.score) / 3.0
    
    feedback_parts = [f"[{s.name}] {s.feedback}" for s in sub_scores]

    return Observation(
        scenario_id=action.scenario_id,
        action_type=action.action_type,
        total_score=round(max(0.0, min(1.0, total)), 4),
        sub_scores=sub_scores,
        feedback=" | ".join(feedback_parts),
    )
