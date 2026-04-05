"""
OptiMaintainer — Dependency Updater Grader (Hard Track)

Weighted score formula:
    total = 0.2 × version_score + 0.4 × breaking_recall + 0.4 × migration_score

Strict rule: NO LLMs in this loop.
Migration quality is evaluated with keyword overlap against the scenario_bank
reference keywords.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from models import (
    Action,
    DependencyActionPayload,
    DependencyUpdate,
    Observation,
    SubScore,
)


def _normalize_version(v: str) -> str:
    """Strip leading 'v' or '=' and whitespace."""
    return re.sub(r"^[v=\s]+", "", v.strip())


def _version_score(agent_updates: List[DependencyUpdate], ref_updates: List[Dict[str, Any]]) -> SubScore:
    """
    Score how well the agent identified the correct target versions.
    """
    ref_map: Dict[str, str] = {
        r["package"].lower(): _normalize_version(r["to_version"])
        for r in ref_updates
    }

    if not ref_map:
        return SubScore(name="version", score=1.0, feedback="Correct: no version updates needed")

    hits = 0
    details: List[str] = []
    for upd in agent_updates:
        pkg = upd.package.lower()
        if pkg in ref_map:
            expected = ref_map[pkg]
            actual = _normalize_version(upd.to_version)
            if actual == expected:
                hits += 1
                details.append(f"✓ '{upd.package}' updated to correct version {actual}")
            else:
                details.append(f"✗ '{upd.package}': expected {expected}, got {actual}")

    score = hits / len(ref_map)
    msg = f"Version Accuracy: identified {hits}/{len(ref_map)} target versions correctly"
    if details:
        msg += " (" + "; ".join(details) + ")"
        
    return SubScore(
        name="version",
        score=round(score, 4),
        feedback=msg,
    )


def _breaking_recall(agent_updates: List[DependencyUpdate], ref_updates: List[Dict[str, Any]]) -> SubScore:
    """
    Recall on correctly flagging breaking changes.
    """
    ref_breaking: Dict[str, bool] = {
        r["package"].lower(): True
        for r in ref_updates
        if r.get("is_breaking", False)
    }

    if not ref_breaking:
        return SubScore(name="breaking_recall", score=1.0, feedback="Correct: no breaking changes in reference")

    agent_map: Dict[str, bool] = {u.package.lower(): u.is_breaking for u in agent_updates}

    hits = 0
    details: List[str] = []
    for pkg in ref_breaking:
        if agent_map.get(pkg, False):
            hits += 1
            details.append(f"✓ {pkg} correctly flagged as breaking")
        else:
            details.append(f"✗ {pkg} breaking change missed")

    score = hits / len(ref_breaking)
    msg = f"Breaking Change Recall: {hits}/{len(ref_breaking)} breaking updates successfully flagged"
    if details:
        msg += " (" + "; ".join(details) + ")"
        
    return SubScore(
        name="breaking_recall",
        score=round(score, 4),
        feedback=msg,
    )


def _tokenize(text: str) -> Set[str]:
    """Simple whitespace + punctuation tokenizer for keyword overlap."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def _migration_score(agent_updates: List[DependencyUpdate], ref_updates: List[Dict[str, Any]]) -> SubScore:
    """
    Score migration notes quality via keyword overlap.
    """
    scored_packages: List[str] = []
    scores: List[float] = []

    ref_migration: Dict[str, List[str]] = {
        r["package"].lower(): [kw.lower() for kw in r["migration_keywords"]]
        for r in ref_updates
        if r.get("migration_keywords")
    }

    if not ref_migration:
        return SubScore(name="migration", score=1.0, feedback="Correct: no migration notes required")

    agent_map: Dict[str, str] = {u.package.lower(): u.migration_notes for u in agent_updates}

    for pkg, ref_kws in ref_migration.items():
        agent_notes = agent_map.get(pkg, "")
        agent_tokens = _tokenize(agent_notes)
        ref_kw_set = set(ref_kws)

        if not ref_kw_set:
            continue

        overlap = len(agent_tokens & ref_kw_set) / len(ref_kw_set)
        scores.append(overlap)
        scored_packages.append(f"{pkg}: {overlap:.0%} overlap with expected migration concepts")

    if not scores:
        return SubScore(name="migration", score=0.0, feedback="Failure: migration notes were missing or lacked key terms")

    avg = sum(scores) / len(scores)
    return SubScore(
        name="migration",
        score=round(avg, 4),
        feedback="Migration Analysis Quality: " + "; ".join(scored_packages),
    )


def grade(action: Action, reference: Dict[str, Any]) -> Observation:
    """
    Grade a dependency-update action.
    Formula: 0.2 × version + 0.4 × breaking_recall + 0.4 × migration
    """
    payload = action.parse_dependency()
    ref_updates: List[Dict[str, Any]] = reference.get("updates", [])

    v_score = _version_score(payload.updates, ref_updates)
    b_score = _breaking_recall(payload.updates, ref_updates)
    m_score = _migration_score(payload.updates, ref_updates)

    total = round(
        0.2 * v_score.score + 0.4 * b_score.score + 0.4 * m_score.score,
        4,
    )

    sub_scores = [v_score, b_score, m_score]
    feedback = (
        f"Version Score: {v_score.score:.2f} (weight 0.2) | "
        f"Breaking Recall: {b_score.score:.2f} (weight 0.4) | "
        f"Migration Analysis: {m_score.score:.2f} (weight 0.4) | "
        f"Final Weighted Total: {total:.4f}"
    )

    return Observation(
        scenario_id=action.scenario_id,
        action_type=action.action_type,
        total_score=max(0.0, min(1.0, total)),
        sub_scores=sub_scores,
        feedback=feedback,
    )
