"""
OptiMaintainer — "Tanish Part" Final Audit Test Suite

Comprehensive edge-case tests verifying every mathematical constraint
from the META HACKATHON Day 2 & Day 3 grading rubrics.
"""

import httpx
import json
import sys

BASE = "http://localhost:8000"

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def reset():
    r = httpx.post(f"{BASE}/reset")
    assert r.status_code == 200
    return r.json()


# ═══════════════════════════════════════════════
#  SECTION 1: TRIAGE GRADER LOGIC
# ═══════════════════════════════════════════════

def audit_triage():
    print("\n" + "═" * 60)
    print("  AUDIT 1: TRIAGE GRADER")
    print("═" * 60)

    reset()

    # --- 1A: category_score is binary 1.0/0.0 ---
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    d = r.json()
    cat_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "category")
    check("category_score exact match = 1.0", cat_score == 1.0, f"got {cat_score}")

    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "feature", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    d = r.json()
    cat_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "category")
    check("category_score wrong = 0.0 (binary)", cat_score == 0.0, f"got {cat_score}")

    # --- 1B: severity_score ordinal distance ---
    reset()

    # Exact match (low=0 vs low=0, diff=0)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-004",
        "payload": {"category": "documentation", "severity": "low",
                    "assignee": "oncall:docs", "decision": "continue"}
    })
    d = r.json()
    sev_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "severity")
    check("severity exact match = 1.0", sev_score == 1.0, f"got {sev_score}")

    reset()
    # 1 level off (expected medium=1, got high=2, diff=1)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-002",
        "payload": {"category": "feature", "severity": "high",
                    "assignee": "oncall:pt2", "decision": "continue"}
    })
    d = r.json()
    sev_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "severity")
    check("severity 1 level off = 0.5", sev_score == 0.5, f"got {sev_score}")

    reset()
    # 2 levels off (expected high=2, got low=0, diff=2)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "low",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    d = r.json()
    sev_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "severity")
    check("severity 2 levels off = 0.0", sev_score == 0.0, f"got {sev_score}")

    reset()
    # 3 levels off (expected critical=3, got low=0, diff=3)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-003",
        "payload": {"category": "bug", "severity": "low",
                    "assignee": "oncall:serialization", "decision": "stop"}
    })
    d = r.json()
    sev_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "severity")
    check("severity 3 levels off = 0.0", sev_score == 0.0, f"got {sev_score}")

    # --- 1C: STOP/CONTINUE routing rules ---
    reset()
    # oncall:distributed → STOP
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    d = r.json()
    dec_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "decision")
    check("oncall:distributed → STOP = 1.0", dec_score == 1.0, f"got {dec_score}")

    # oncall:pt2 → CONTINUE
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-002",
        "payload": {"category": "feature", "severity": "medium",
                    "assignee": "oncall:pt2", "decision": "continue"}
    })
    d = r.json()
    dec_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "decision")
    check("oncall:pt2 → CONTINUE = 1.0", dec_score == 1.0, f"got {dec_score}")

    # Wrong decision for oncall:distributed
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "continue"}
    })
    d = r.json()
    dec_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "decision")
    check("oncall:distributed → CONTINUE (wrong) = 0.0", dec_score == 0.0, f"got {dec_score}")

    # --- 1D: Routing score: exact, domain, wrong ---
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    d = r.json()
    rte_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "routing")
    check("routing exact assignee = 1.0", rte_score == 1.0, f"got {rte_score}")

    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:ci", "decision": "stop"}
    })
    d = r.json()
    rte_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "routing")
    check("routing correct domain = 0.5", rte_score == 0.5, f"got {rte_score}")

    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "random_person", "decision": "stop"}
    })
    d = r.json()
    rte_score = next(s["score"] for s in d["sub_scores"] if s["name"] == "routing")
    check("routing wrong = 0.0", rte_score == 0.0, f"got {rte_score}")


# ═══════════════════════════════════════════════
#  SECTION 2: SECURITY GRADER LOGIC
# ═══════════════════════════════════════════════

def audit_security():
    print("\n" + "═" * 60)
    print("  AUDIT 2: SECURITY GRADER")
    print("═" * 60)

    # --- 2A: ±2 line buffer ---
    reset()
    # Exact line
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 2, "fix_description": "Use parameterized queries"}
        ]}
    })
    d = r.json()
    check("finding match at exact line", d["total_score"] == 1.0, f"got {d['total_score']}")

    reset()
    # +2 lines (within buffer)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 4, "fix_description": "Use parameterized queries"}
        ]}
    })
    d = r.json()
    check("finding match at +2 lines (within ±2)", d["total_score"] == 1.0, f"got {d['total_score']}")

    reset()
    # -2 lines (within buffer, but line_number must be >= 1 so test at line 1, which is -1 from ref 2)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 1, "fix_description": "Use parameterized queries"}
        ]}
    })
    d = r.json()
    check("finding match at -1 line (within ±2)", d["total_score"] == 1.0, f"got {d['total_score']}")

    reset()
    # +3 lines (outside buffer)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 5, "fix_description": "Use parameterized queries"}
        ]}
    })
    d = r.json()
    # Should be 0 (no match) + missed critical → 0.0 * 0.7 - 0.05 FP
    check("finding at +3 lines → outside ±2 buffer (no match)", d["total_score"] == 0.0, f"got {d['total_score']}")

    # --- 2B: 0.6 base + 0.4 keyword bonus ---
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 2, "fix_description": "Use parameterized queries"}
        ]}
    })
    d = r.json()
    finding_sub = next((s for s in d["sub_scores"] if s["name"].startswith("finding_")), None)
    check("match score: 0.6 base + 0.4 keyword = 1.0", finding_sub and finding_sub["score"] == 1.0,
          f"got {finding_sub['score'] if finding_sub else 'None'}")

    reset()
    # No keyword in fix
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 2, "fix_description": "Fix the code somehow"}
        ]}
    })
    d = r.json()
    finding_sub = next((s for s in d["sub_scores"] if s["name"].startswith("finding_")), None)
    check("match score without keywords: 0.6 only", finding_sub and finding_sub["score"] == 0.6,
          f"got {finding_sub['score'] if finding_sub else 'None'}")

    # --- 2C: 0.7x multiplier for missed CRITICAL ---
    reset()
    # security-003 has 2 vulns: CWE-502 at line 4 (critical) + CWE-502 at line 8 (high)
    # Submit only the high one, missing the critical
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-003",
        "payload": {"findings": [
            {"cwe_id": "CWE-502", "line_number": 8, "fix_description": "Use yaml.safe_load"}
        ]}
    })
    d = r.json()
    has_recall_penalty = any(s["name"] == "recall_penalty" for s in d["sub_scores"])
    check("0.7x recall penalty applied when CRITICAL missed", has_recall_penalty,
          f"sub_scores: {[s['name'] for s in d['sub_scores']]}")

    # --- 2D: 0.05 per false positive, max 0.2 ---
    reset()
    # Submit 5 FPs against security-004 (1 real vuln + 5 fake)
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-004",
        "payload": {"findings": [
            {"cwe_id": "CWE-22", "line_number": 3, "fix_description": "Use realpath"},
            {"cwe_id": "CWE-89", "line_number": 10, "fix_description": "fake"},
            {"cwe_id": "CWE-79", "line_number": 20, "fix_description": "fake"},
            {"cwe_id": "CWE-78", "line_number": 30, "fix_description": "fake"},
            {"cwe_id": "CWE-502", "line_number": 40, "fix_description": "fake"},
            {"cwe_id": "CWE-918", "line_number": 50, "fix_description": "fake"},
        ]}
    })
    d = r.json()
    fp_sub = next((s for s in d["sub_scores"] if s["name"] == "fp_penalty"), None)
    # 5 FPs × 0.05 = 0.25, capped at 0.2 → score should show 0.8
    check("FP penalty capped at 0.2 (5 FPs)", fp_sub and fp_sub["score"] == 0.8,
          f"got {fp_sub['score'] if fp_sub else 'None'}")
    # Total: real match = 1.0 → 1.0/1 = 1.0 - 0.2 = 0.8
    check("total with max FP penalty = 0.8", d["total_score"] == 0.8, f"got {d['total_score']}")

    # --- 2E: Perfect security (no FP, no miss, keywords match) ---
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "security-001",
        "payload": {"findings": [
            {"cwe_id": "CWE-89", "line_number": 2, "fix_description": "Use parameterized queries"}
        ]}
    })
    d = r.json()
    check("perfect security score = 1.0", d["total_score"] == 1.0, f"got {d['total_score']}")


# ═══════════════════════════════════════════════
#  SECTION 3: DEPENDENCY GRADER LOGIC
# ═══════════════════════════════════════════════

def audit_dependency():
    print("\n" + "═" * 60)
    print("  AUDIT 3: DEPENDENCY GRADER")
    print("═" * 60)

    # --- 3A: No LLM calls (already verified via grep, re-confirm here) ---
    import importlib
    dep_mod = importlib.import_module("server.dependency_grader")
    source_file = dep_mod.__file__
    with open(source_file, "r") as f:
        source = f.read()
    no_llm = not any(
        line.strip().startswith(("import ", "from ")) and
        any(kw in line.lower() for kw in [
            "openai", "anthropic", "langchain", "transformers", "torch"
        ])
        for line in source.splitlines()
    )
    check("CRITICAL: No LLM imports in dependency_grader.py", no_llm)

    # --- 3B: Weighted formula 0.2v + 0.4b + 0.4m ---
    check("formula: 0.2*version + 0.4*breaking + 0.4*migration in source",
          "0.2 * v_score.score + 0.4 * b_score.score + 0.4 * m_score.score" in source)

    # --- 3C: Perfect dependency score ---
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "dependency", "scenario_id": "dependency-004",
        "payload": {"updates": [{
            "package": "requests",
            "from_version": "2.31.0",
            "to_version": "2.32.3",
            "is_breaking": False,
            "migration_notes": "This is a bugfix patch update for session handling and certificate verification"
        }]}
    })
    d = r.json()
    v = next(s for s in d["sub_scores"] if s["name"] == "version")
    b = next(s for s in d["sub_scores"] if s["name"] == "breaking_recall")
    m = next(s for s in d["sub_scores"] if s["name"] == "migration")

    check("version score = 1.0 (correct version)", v["score"] == 1.0, f"got {v['score']}")
    check("breaking_recall = 1.0 (non-breaking correctly)", b["score"] == 1.0, f"got {b['score']}")
    # migration: keywords = session, certificate, bugfix, patch → agent has all 4
    check("migration score > 0 (keyword overlap)", m["score"] > 0, f"got {m['score']}")

    expected_total = round(0.2 * v["score"] + 0.4 * b["score"] + 0.4 * m["score"], 4)
    check(f"weighted total matches formula: {expected_total}", d["total_score"] == expected_total,
          f"got {d['total_score']}")

    # --- 3D: Wrong version ---
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "dependency", "scenario_id": "dependency-004",
        "payload": {"updates": [{
            "package": "requests",
            "from_version": "2.31.0",
            "to_version": "2.33.0",  # wrong version
            "is_breaking": False,
            "migration_notes": "session certificate bugfix patch"
        }]}
    })
    d = r.json()
    v = next(s for s in d["sub_scores"] if s["name"] == "version")
    check("version score = 0.0 (wrong version)", v["score"] == 0.0, f"got {v['score']}")

    # --- 3E: Missing breaking flag ---
    reset()
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "dependency", "scenario_id": "dependency-001",
        "payload": {"updates": [{
            "package": "numpy",
            "from_version": "1.24.4",
            "to_version": "2.0.0",
            "is_breaking": False,  # should be True
            "migration_notes": "deprecated int64 distutils string repr dtype api removed ravel ndarray"
        }]}
    })
    d = r.json()
    b = next(s for s in d["sub_scores"] if s["name"] == "breaking_recall")
    check("breaking_recall = 0.0 (missed breaking flag)", b["score"] == 0.0, f"got {b['score']}")

    # --- 3F: Migration keywords from scenario_bank (not hardcoded in grader) ---
    with open("scenario_bank.json", "r") as f:
        bank = json.load(f)
    dep_scenarios = [s for s in bank["scenarios"] if s["type"] == "dependency"]
    all_have_keywords = all(
        any(u.get("migration_keywords") for u in s["reference"]["updates"])
        for s in dep_scenarios
    )
    check("migration_keywords stored in scenario_bank (not hardcoded)", all_have_keywords)


# ═══════════════════════════════════════════════
#  SECTION 4: DOCKER & DEPLOYMENT AUDIT
# ═══════════════════════════════════════════════

def audit_docker():
    print("\n" + "═" * 60)
    print("  AUDIT 4: DOCKER & DEPLOYMENT")
    print("═" * 60)

    with open("Dockerfile", "r") as f:
        dockerfile = f.read()

    check("Base image: python:3.11-slim", "FROM python:3.11-slim" in dockerfile)
    check("HEALTHCHECK with curl to :8000/health",
          "curl" in dockerfile and "localhost:8000/health" in dockerfile)

    # Requirements pinned
    with open("requirements.txt", "r") as f:
        reqs = f.read().strip().split("\n")
    all_pinned = all("==" in r for r in reqs if r.strip())
    no_gte = not any(">=" in r for r in reqs)
    check("All deps pinned with == (no >=)", all_pinned and no_gte,
          f"lines: {reqs}")

    # Layer caching: requirements.txt copied BEFORE app code
    req_pos = dockerfile.index("COPY requirements.txt")
    app_pos = dockerfile.index("COPY models.py")
    check("requirements.txt installed BEFORE app code (layer caching)", req_pos < app_pos)

    # No heavy ML libs
    heavy = ["torch", "tensorflow", "transformers", "jax"]
    reqs_lower = " ".join(reqs).lower()
    no_heavy = not any(h in reqs_lower for h in heavy)
    check("No heavy ML libraries in requirements.txt", no_heavy)


# ═══════════════════════════════════════════════
#  SECTION 5: SCENARIO BANK VALIDATION
# ═══════════════════════════════════════════════

def audit_scenario_bank():
    print("\n" + "═" * 60)
    print("  AUDIT 5: SCENARIO BANK")
    print("═" * 60)

    with open("scenario_bank.json", "r") as f:
        bank = json.load(f)

    scenarios = bank["scenarios"]
    check(f"Total scenarios >= 15", len(scenarios) >= 15, f"got {len(scenarios)}")

    triage = [s for s in scenarios if s["type"] == "triage"]
    security = [s for s in scenarios if s["type"] == "security"]
    dependency = [s for s in scenarios if s["type"] == "dependency"]

    check(f"5 triage scenarios", len(triage) == 5, f"got {len(triage)}")
    check(f"5 security scenarios", len(security) == 5, f"got {len(security)}")
    check(f"5 dependency scenarios", len(dependency) == 5, f"got {len(dependency)}")

    # All scenarios have unique IDs
    ids = [s["id"] for s in scenarios]
    check("All scenario IDs are unique", len(ids) == len(set(ids)))

    # All have reference + context
    all_ref = all("reference" in s for s in scenarios)
    all_ctx = all("context" in s for s in scenarios)
    check("All scenarios have reference answers", all_ref)
    check("All scenarios have context", all_ctx)


# ═══════════════════════════════════════════════
#  SECTION 6: API CONTRACT TESTS
# ═══════════════════════════════════════════════

def audit_api():
    print("\n" + "═" * 60)
    print("  AUDIT 6: API CONTRACTS")
    print("═" * 60)

    # Health
    r = httpx.get(f"{BASE}/health")
    check("/health returns 200", r.status_code == 200)
    check("/health returns {status: ok}", r.json() == {"status": "ok"})

    # Reset
    r = httpx.post(f"{BASE}/reset")
    check("/reset returns 200", r.status_code == 200)
    d = r.json()
    check("/reset has message field", "message" in d)
    check("/reset has total_scenarios", "total_scenarios" in d)
    check("/reset has scenario_ids list", isinstance(d.get("scenario_ids"), list))

    # Step returns Observation schema
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    d = r.json()
    check("/step returns scenario_id", "scenario_id" in d)
    check("/step returns action_type", "action_type" in d)
    check("/step returns total_score [0,1]", 0.0 <= d["total_score"] <= 1.0)
    check("/step returns sub_scores array", isinstance(d.get("sub_scores"), list))
    check("/step returns feedback string", isinstance(d.get("feedback"), str))
    check("/step returns done boolean", isinstance(d.get("done"), bool))

    # Duplicate submission → 409
    r2 = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "triage-001",
        "payload": {"category": "bug", "severity": "high",
                    "assignee": "oncall:distributed", "decision": "stop"}
    })
    check("duplicate submission returns 409", r2.status_code == 409)

    # Wrong action_type → 422
    reset()
    r3 = httpx.post(f"{BASE}/step", json={
        "action_type": "security", "scenario_id": "triage-001",
        "payload": {"findings": []}
    })
    check("mismatched action_type returns 422", r3.status_code == 422)

    # Unknown scenario → 404
    r4 = httpx.post(f"{BASE}/step", json={
        "action_type": "triage", "scenario_id": "fake-999",
        "payload": {}
    })
    check("unknown scenario returns 404", r4.status_code == 404)

    # State endpoint
    reset()
    r5 = httpx.get(f"{BASE}/state")
    check("/state returns 200", r5.status_code == 200)


# ═══════════════════════════════════════════════
#  MAIN RUNNER
# ═══════════════════════════════════════════════

def main():
    print("╔" + "═" * 58 + "╗")
    print("║  OptiMaintainer — 'Tanish Part' Final Audit             ║")
    print("║  META HACKATHON Day 2/3 Rubric Compliance               ║")
    print("╚" + "═" * 58 + "╝")

    audit_triage()
    audit_security()
    audit_dependency()
    audit_docker()
    audit_scenario_bank()
    audit_api()

    print("\n" + "═" * 60)
    print(f"  FINAL RESULTS: {PASS} passed, {FAIL} failed")
    print("═" * 60)

    if FAIL == 0:
        print("\n  🏆 100% COMPLIANCE — READY FOR SUBMISSION\n")
    else:
        print(f"\n  ⚠️  {FAIL} ISSUE(S) NEED FIXING\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("❌ Server not running on localhost:8000")
        sys.exit(1)
