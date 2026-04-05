from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from models import (
    Action,
    DependencyAction,
    DependencyUpdate,
    Reward,
    SecurityAuditAction,
    TriageAction,
)

# --- Ordinal mapping for severity ---
_SEVERITY_ORD: Dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

def grade_triage(action: TriageAction, ground_truth: Dict[str, Any]) -> Reward:
    """Grade a triage action. Each dimension weighted 0.25 each."""
    
    # 1. Category (exactly binary)
    cat_match = 1.0 if action.category.lower().strip() == ground_truth["category"].lower().strip() else 0.0

    # 2. Severity (ordinal distance)
    p_ord = _SEVERITY_ORD.get(action.severity.lower(), 0)
    e_ord = _SEVERITY_ORD.get(ground_truth["severity"].lower(), 0)
    diff = abs(p_ord - e_ord)
    if diff == 0:
        sev_score = 1.0
    elif diff == 1:
        sev_score = 0.5
    else:
        sev_score = 0.0

    # 3. Routing (exact assignee or domain)
    pred_assignee = action.assignee.lower().strip()
    exp_assignee = ground_truth["assignee"].lower().strip()
    exp_domain = ground_truth.get("domain", "").lower().strip()
    
    if pred_assignee == exp_assignee:
        rot_score = 1.0
    elif exp_domain and pred_assignee.startswith(exp_domain):
        rot_score = 0.5
    else:
        rot_score = 0.0

    # 4. Decision (logical policy)
    # oncall:distributed → STOP, oncall:pt2 → CONTINUE
    # Reference decision from scenario_bank
    exp_decision = ground_truth["decision"].lower().strip()
    pred_decision = action.decision.lower().strip()
    dec_score = 1.0 if pred_decision == exp_decision else 0.0

    sub_scores = {
        "category": cat_match,
        "severity": sev_score,
        "routing": rot_score,
        "decision": dec_score,
    }

    total_score = sum(sub_scores.values()) / 4.0
    return Reward(
        total_score=round(total_score, 4),
        sub_scores=sub_scores,
        feedback=f"Grade: cat={cat_match}, sev={sev_score}, routing={rot_score}, dec={dec_score}",
        is_terminal=True,
    )


# --- Security Keywords ---
_SEC_KEYWORDS: Dict[str, List[str]] = {
    "CWE-89": ["parameterized", "prepared statement", "bound parameter", "sanitize"],
    "CWE-79": ["escape", "encode", "sanitize", "csp", "dompurify", "innertext"],
    "CWE-502": ["safe loader", "json", "allowlist", "deserialize", "yaml.safe_load"],
    "CWE-22": ["canonicalize", "realpath", "basename", "path traversal"],
    "CWE-918": ["allowlist", "ssrf", "url validation", "internal", "deny list"],
}

def _security_keyword_match(cwe_id: str, desc: str) -> float:
    keywords = _SEC_KEYWORDS.get(cwe_id.upper(), [])
    if not keywords: return 0.0
    desc_lower = desc.lower()
    return 1.0 if any(kw in desc_lower for kw in keywords) else 0.0

def grade_security_audit(action: SecurityAuditAction, ground_truth: Dict[str, Any]) -> Reward:
    """Grade security findings. 0.6 base + 0.4 keyword. Penalty for missed critical. FP penalty -0.05."""
    ref_vulns = ground_truth.get("vulnerabilities", ground_truth.get("findings", []))
    
    matched_indices = set()
    sub_scores = {}
    finding_total_credit = 0.0
    false_positives = 0
    
    # 1. Findings Matcher
    for i, f in enumerate(action.findings):
        matched = False
        for idx, ref in enumerate(ref_vulns):
            if idx in matched_indices: continue
            if f.cwe_id.upper() != ref["cwe_id"].upper(): continue
            if abs(f.line_number - ref["line_number"]) > 2: continue
            
            # Match!
            matched = True
            matched_indices.add(idx)
            kw_score = _security_keyword_match(ref["cwe_id"], f.fix_description)
            score = 0.6 + (0.4 * kw_score)
            sub_scores[f"finding_{f.cwe_id}_{f.line_number}"] = score
            finding_total_credit += score
            break
        
        if not matched:
            false_positives += 1

    # 2. Recall Score
    if ref_vulns:
        recall = finding_total_credit / len(ref_vulns)
    else:
        recall = 1.0 if not action.findings else 0.0

    # 3. Recall Penalty (0.7x if CRITICAL missed)
    missed_critical = False
    for idx, ref in enumerate(ref_vulns):
        if idx not in matched_indices:
            if ref.get("severity", "").upper() == "CRITICAL":
                missed_critical = True
                break
    
    recall_penalty = 1.0
    if missed_critical:
        recall *= 0.7
        recall_penalty = 0.7
    
    sub_scores["recall_penalty"] = recall_penalty

    # 4. FP Penalty (-0.05 each, max -0.2)
    # The requirement says "subtract 0.05 per FP". 
    # Usually this is subtracted from the total recall [0,1].
    penalty_val = min(false_positives * 0.05, 0.2)
    final_score = max(0.0, recall - penalty_val)
    sub_scores["fp_penalty"] = round(1.0 - penalty_val, 2)

    return Reward(
        total_score=round(final_score, 4),
        sub_scores=sub_scores,
        feedback=f"Found {len(matched_indices)}/{len(ref_vulns)} vulns with {false_positives} FPs.",
        is_terminal=True,
    )


def _tokenize(text: str) -> Set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))

def grade_dependency(action: DependencyAction, ground_truth: Dict[str, Any]) -> Reward:
    """Grade dependency updates. Weights: 0.2 v + 0.4 b + 0.4 m."""
    ref_updates = ground_truth.get("updates", [])
    agent_updates = action.updates

    # 1. Version Score
    ref_versions = {u["package"].lower(): u["to_version"].strip("v= ") for u in ref_updates}
    v_hits = 0
    for upd in agent_updates:
        pkg = upd.package.lower()
        if pkg in ref_versions and upd.to_version.strip("v= ") == ref_versions[pkg]:
            v_hits += 1
    v_score = v_hits / len(ref_versions) if ref_versions else 1.0

    # 2. Breaking Recall
    ref_breaking = {u["package"].lower() for u in ref_updates if u.get("is_breaking")}
    b_hits = 0
    for upd in agent_updates:
        if upd.package.lower() in ref_breaking and upd.is_breaking:
            b_hits += 1
    b_recall = b_hits / len(ref_breaking) if ref_breaking else 1.0

    # 3. Migration (Keyword Overlap)
    m_scores = []
    for u in ref_updates:
        kws = u.get("migration_keywords")
        if not kws: continue
        
        pkg = u["package"].lower()
        agent_note = next((upd.migration_notes for upd in agent_updates if upd.package.lower() == pkg), "")
        agent_tokens = _tokenize(agent_note)
        kw_set = {kw.lower() for kw in kws}
        
        if not kw_set:
            m_scores.append(1.0)
        else:
            overlap = len(agent_tokens & kw_set) / len(kw_set)
            m_scores.append(overlap)
    
    m_score = sum(m_scores) / len(m_scores) if m_scores else 1.0

    total = (0.2 * v_score) + (0.4 * b_recall) + (0.4 * m_score)
    sub_scores = {
        "version": round(v_score, 4),
        "breaking_recall": round(b_recall, 4),
        "migration": round(m_score, 4),
    }

    return Reward(
        total_score=round(total, 4),
        sub_scores=sub_scores,
        feedback=f"v={v_score:.2f}, b={b_recall:.2f}, m={m_score:.2f}",
        is_terminal=True,
    )

GRADER_MAP = {
    "triage": grade_triage,
    "security": grade_security_audit,
    "dependency": grade_dependency,
    "task_triage": grade_triage,
    "task_security_audit": grade_security_audit,
    "task_dependency_update": grade_dependency,
}
