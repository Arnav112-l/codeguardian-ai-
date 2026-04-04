"""
OptiMaintainer — Security Audit Grader (Medium Track)

Scoring logic:
  1. finding_matcher  — match agent findings to reference vulnerabilities
     • cwe_id must match exactly
     • line_number must be within ±2 lines
     • matching finding: 0.6 base + 0.4 keyword-fix bonus
  2. recall_penalty   — multiply total by 0.7 if any CRITICAL vuln is missed
  3. false_positive    — deduct 0.05 per false positive (max 0.2 deduction)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from models import (
    Action,
    Observation,
    SecurityActionPayload,
    SecurityFinding,
    SubScore,
)

# CWE → keywords expected in a good fix description
_FIX_KEYWORDS: Dict[str, List[str]] = {
    "CWE-89": ["parameterized", "prepared statement", "bound parameter", "sanitize", "escape"],
    "CWE-79": ["escape", "encode", "sanitize", "csp", "dompurify", "innertext"],
    "CWE-78": ["allowlist", "whitelist", "subprocess", "shlex", "shell=false", "avoid shell"],
    "CWE-22": ["canonicalize", "realpath", "basename", "path traversal", "chroot"],
    "CWE-502": ["safe loader", "json", "allowlist", "deserialize", "yaml.safe_load"],
    "CWE-918": ["allowlist", "ssrf", "url validation", "internal", "deny list"],
    "CWE-327": ["aes", "sha-256", "bcrypt", "argon2", "modern cipher", "strong hash"],
    "CWE-798": ["environment variable", "vault", "secret manager", "config", "rotate"],
    "CWE-611": ["disable external entities", "xxe", "defusedxml", "disallow_doctype"],
    "CWE-434": ["file type", "mime", "magic bytes", "extension whitelist", "content-type"],
}

LINE_TOLERANCE = 2  # ±2 lines


def _keyword_match_score(cwe_id: str, fix_description: str) -> float:
    """Return 1.0 if any expected keyword appears in the fix description, else 0.0."""
    keywords = _FIX_KEYWORDS.get(cwe_id.upper(), [])
    if not keywords:
        return 0.0
    desc_lower = fix_description.lower()
    return 1.0 if any(kw in desc_lower for kw in keywords) else 0.0


def _match_finding(
    agent_finding: SecurityFinding,
    ref_vulns: List[Dict[str, Any]],
    already_matched: Set[int],
) -> Tuple[Optional[int], float, str]:
    """
    Try to match an agent finding to a reference vuln.

    Returns (matched_idx | None, score, feedback_str).
    """
    for idx, ref in enumerate(ref_vulns):
        if idx in already_matched:
            continue

        # CWE must match exactly (case-insensitive)
        if agent_finding.cwe_id.upper() != ref["cwe_id"].upper():
            continue

        # Line number within tolerance
        if abs(agent_finding.line_number - ref["line_number"]) > LINE_TOLERANCE:
            continue

        # Base score 0.6 for a valid match
        base = 0.6
        kw_bonus = 0.4 * _keyword_match_score(ref["cwe_id"], agent_finding.fix_description)
        score = base + kw_bonus

        feedback = (
            f"Matched {ref['cwe_id']} at line {ref['line_number']} "
            f"(agent line {agent_finding.line_number}): "
            f"base=0.6 + keyword_bonus={kw_bonus:.2f}"
        )
        return idx, score, feedback

    return None, 0.0, ""


def grade(action: Action, reference: Dict[str, Any]) -> Observation:
    """
    Grade a security-audit action against the reference vulnerabilities.

    Parameters
    ----------
    action : Action
        Agent's submitted security findings.
    reference : dict
        Expected answer with key 'vulnerabilities': list of dicts with
        cwe_id, line_number, severity, fix_keywords.

    Returns
    -------
    Observation with sub_scores and total_score.
    """
    payload = action.parse_security()
    ref_vulns: List[Dict[str, Any]] = reference.get("vulnerabilities", [])

    matched_indices: Set[int] = set()
    finding_scores: List[float] = []
    sub_scores: List[SubScore] = []
    feedback_parts: List[str] = []

    # --- Score each agent finding ---
    false_positives = 0
    for f in payload.findings:
        matched_idx, score, fb = _match_finding(f, ref_vulns, matched_indices)
        if matched_idx is not None:
            matched_indices.add(matched_idx)
            finding_scores.append(score)
            sub_scores.append(SubScore(name=f"finding_{f.cwe_id}", score=score, feedback=fb))
            feedback_parts.append(fb)
        else:
            false_positives += 1
            fb = f"False positive: {f.cwe_id} at line {f.line_number}"
            sub_scores.append(SubScore(name=f"fp_{f.cwe_id}_{f.line_number}", score=0.0, feedback=fb))
            feedback_parts.append(fb)

    # --- Missed vulnerabilities ---
    missed_critical = False
    for idx, ref in enumerate(ref_vulns):
        if idx not in matched_indices:
            sev = ref.get("severity", "unknown")
            fb = f"Missed {ref['cwe_id']} at line {ref['line_number']} (severity: {sev})"
            sub_scores.append(SubScore(name=f"missed_{ref['cwe_id']}", score=0.0, feedback=fb))
            feedback_parts.append(fb)
            if sev.lower() == "critical":
                missed_critical = True

    # --- Compute raw score ---
    if ref_vulns:
        raw_score = sum(finding_scores) / len(ref_vulns)
    else:
        raw_score = 1.0 if not payload.findings else 0.0

    # --- Recall penalty: multiply by 0.7 if CRITICAL missed ---
    if missed_critical:
        raw_score *= 0.7
        feedback_parts.append("⚠ CRITICAL vulnerability missed → 0.7× recall penalty applied")
        sub_scores.append(SubScore(name="recall_penalty", score=0.7, feedback="0.7× multiplier for missed CRITICAL"))

    # --- False positive penalty: -0.05 each, max -0.2 ---
    fp_penalty = min(false_positives * 0.05, 0.2)
    if fp_penalty > 0:
        raw_score = max(0.0, raw_score - fp_penalty)
        fb = f"False positive penalty: -{fp_penalty:.2f} ({false_positives} FPs)"
        feedback_parts.append(fb)
        sub_scores.append(SubScore(name="fp_penalty", score=round(1.0 - fp_penalty, 2), feedback=fb))

    total = round(max(0.0, min(1.0, raw_score)), 4)

    return Observation(
        scenario_id=action.scenario_id,
        action_type=action.action_type,
        total_score=total,
        sub_scores=sub_scores,
        feedback=" | ".join(feedback_parts) if feedback_parts else "No findings submitted",
    )
