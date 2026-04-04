from __future__ import annotations

from typing import Any

from models import (
    DependencyAction,
    Reward,
    SecurityAuditAction,
    TriageAction,
)


def grade_triage(action: TriageAction, ground_truth: dict[str, Any]) -> Reward:
    """Grade a triage action against ground truth.
    
    Weights: category=0.4, severity=0.3, module_label=0.2, oncall_routing=0.1
    """
    sub_scores = {
        "category_match": 1.0 if action.category == ground_truth["category"] else 0.0,
        "severity_match": 1.0 if action.severity == ground_truth["severity"] else 0.0,
        "module_match": 1.0 if action.module_label == ground_truth["module_label"] else 0.0,
        "routing_match": 1.0 if action.oncall_routing == ground_truth["oncall_routing"] else 0.0,
    }

    total_score = (
        sub_scores["category_match"] * 0.4
        + sub_scores["severity_match"] * 0.3
        + sub_scores["module_match"] * 0.2
        + sub_scores["routing_match"] * 0.1
    )
    total_score = max(0.0, min(1.0, total_score))

    return Reward.model_validate(
        {
            "total_score": round(total_score, 4),
            "sub_scores": sub_scores,
            "feedback": "Triage action graded against category, severity, module, and routing.",
            "is_terminal": True,
        }
    )


def grade_security_audit(action: SecurityAuditAction, ground_truth: dict[str, Any]) -> Reward:
    """Grade a security audit action using F1 score on CWE IDs.
    
    Includes partial credit for line_number within ±2.
    """
    expected_findings = ground_truth["findings"]
    expected_cwe_ids = {item["cwe_id"] for item in expected_findings}
    predicted_cwe_ids = {finding.cwe_id for finding in action.findings}

    # Calculate precision and recall for CWE IDs
    if not expected_cwe_ids:
        cwe_recall = 1.0
    else:
        cwe_recall = len(expected_cwe_ids.intersection(predicted_cwe_ids)) / len(expected_cwe_ids)

    if not predicted_cwe_ids:
        cwe_precision = 0.0
    else:
        cwe_precision = len(expected_cwe_ids.intersection(predicted_cwe_ids)) / len(predicted_cwe_ids)

    # F1 score
    if cwe_precision + cwe_recall > 0:
        f1_score = 2 * (cwe_precision * cwe_recall) / (cwe_precision + cwe_recall)
    else:
        f1_score = 0.0

    # Partial credit for line numbers within ±2
    line_credit = 0.0
    if expected_findings and action.findings:
        expected_lines = {item["line_number"] for item in expected_findings}
        for finding in action.findings:
            for expected_line in expected_lines:
                if abs(finding.line_number - expected_line) <= 2:
                    line_credit += 1.0
                    break
        line_credit = line_credit / max(len(expected_findings), len(action.findings))

    sub_scores = {
        "cwe_f1": float(round(f1_score, 4)),
        "line_accuracy": float(round(line_credit, 4)),
    }

    total_score = f1_score * 0.8 + line_credit * 0.2
    total_score = max(0.0, min(1.0, total_score))

    return Reward.model_validate(
        {
            "total_score": round(total_score, 4),
            "sub_scores": sub_scores,
            "feedback": "Security findings graded on CWE F1 score and line number accuracy.",
            "is_terminal": True,
        }
    )


def grade_dependency(action: DependencyAction, ground_truth: dict[str, Any]) -> Reward:
    """Grade a dependency action.
    
    Weights: version_correct=0.4, breaking_changes_f1=0.4, migration_desc_nonempty=0.2
    """
    # Version match
    version_correct = 1.0 if action.updated_version == ground_truth["updated_version"] else 0.0

    # Breaking changes F1 (token-level)
    expected_tokens = set()
    for change in ground_truth["breaking_changes"]:
        expected_tokens.update(change.lower().split())
    
    predicted_tokens = set()
    for change in action.breaking_changes:
        predicted_tokens.update(change.lower().split())

    if not expected_tokens and not predicted_tokens:
        breaking_f1 = 1.0
    elif not expected_tokens or not predicted_tokens:
        breaking_f1 = 0.0
    else:
        intersection = expected_tokens.intersection(predicted_tokens)
        precision = len(intersection) / len(predicted_tokens) if predicted_tokens else 0.0
        recall = len(intersection) / len(expected_tokens) if expected_tokens else 0.0
        if precision + recall > 0:
            breaking_f1 = 2 * (precision * recall) / (precision + recall)
        else:
            breaking_f1 = 0.0

    # Migration description non-empty check
    migration_nonempty = 1.0 if len(action.migration_description.strip()) >= 20 else 0.0

    sub_scores = {
        "version_correct": float(version_correct),
        "breaking_changes_f1": float(round(breaking_f1, 4)),
        "migration_nonempty": float(migration_nonempty),
    }

    total_score = (
        version_correct * 0.4
        + breaking_f1 * 0.4
        + migration_nonempty * 0.2
    )
    total_score = max(0.0, min(1.0, total_score))

    return Reward.model_validate(
        {
            "total_score": round(total_score, 4),
            "sub_scores": sub_scores,
            "feedback": "Dependency recommendation graded on version, breaking changes F1, and migration detail.",
            "is_terminal": True,
        }
    )


GRADER_MAP = {
    "task_triage": grade_triage,
    "task_security_audit": grade_security_audit,
    "task_dependency_update": grade_dependency,
}
