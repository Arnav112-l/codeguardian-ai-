"""
OptiMaintainer — Integration tests

Validates all three grading tracks end-to-end against the running server.
"""

import httpx
import sys

BASE = "http://localhost:8000"


def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    print("✅ /health → ok")


def test_reset():
    r = httpx.post(f"{BASE}/reset")
    assert r.status_code == 200
    data = r.json()
    assert data["total_scenarios"] == 15
    assert len(data["scenario_ids"]) == 15
    print(f"✅ /reset → {data['total_scenarios']} scenarios loaded")


def test_triage_perfect():
    """Submit a perfect triage answer for triage-001."""
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage",
        "scenario_id": "triage-001",
        "payload": {
            "category": "bug",
            "severity": "high",
            "assignee": "oncall:distributed",
            "decision": "stop",
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total_score"] == 1.0, f"Expected 1.0, got {data['total_score']}"
    print(f"✅ triage-001 perfect score → {data['total_score']}")
    print(f"   Feedback: {data['feedback']}")


def test_triage_partial():
    """Submit a partially correct triage answer for triage-002."""
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "triage",
        "scenario_id": "triage-002",
        "payload": {
            "category": "feature",
            "severity": "high",        # wrong: should be medium (1 level off)
            "assignee": "oncall:pt2",
            "decision": "continue",
        },
    })
    assert r.status_code == 200
    data = r.json()
    # category=1.0, severity=0.5, routing=1.0, decision=1.0 → avg=0.875
    assert data["total_score"] == 0.875, f"Expected 0.875, got {data['total_score']}"
    print(f"✅ triage-002 partial score → {data['total_score']}")
    print(f"   Feedback: {data['feedback']}")


def test_security_perfect():
    """Submit a perfect security answer for security-001 (SQL injection)."""
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security",
        "scenario_id": "security-001",
        "payload": {
            "findings": [
                {
                    "cwe_id": "CWE-89",
                    "line_number": 2,
                    "fix_description": "Use parameterized queries with bound parameters",
                }
            ]
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total_score"] == 1.0, f"Expected 1.0, got {data['total_score']}"
    print(f"✅ security-001 perfect score → {data['total_score']}")
    print(f"   Feedback: {data['feedback']}")


def test_security_with_false_positive():
    """Submit security-002 with a correct finding + 1 false positive."""
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "security",
        "scenario_id": "security-002",
        "payload": {
            "findings": [
                {
                    "cwe_id": "CWE-79",
                    "line_number": 2,
                    "fix_description": "Sanitize HTML output using bleach or DOMPurify",
                },
                {
                    "cwe_id": "CWE-502",
                    "line_number": 10,
                    "fix_description": "This is a false positive",
                },
            ]
        },
    })
    assert r.status_code == 200
    data = r.json()
    # base match = 0.6 + 0.4*1.0 = 1.0; 1 FP = -0.05 → 0.95
    assert data["total_score"] == 0.95, f"Expected 0.95, got {data['total_score']}"
    print(f"✅ security-002 with FP → {data['total_score']}")
    print(f"   Feedback: {data['feedback']}")


def test_dependency_perfect():
    """Submit a perfect dependency answer for dependency-004 (non-breaking patch)."""
    r = httpx.post(f"{BASE}/step", json={
        "action_type": "dependency",
        "scenario_id": "dependency-004",
        "payload": {
            "updates": [
                {
                    "package": "requests",
                    "from_version": "2.31.0",
                    "to_version": "2.32.3",
                    "is_breaking": False,
                    "migration_notes": "This is a bugfix patch update for session handling and certificate verification",
                }
            ]
        },
    })
    assert r.status_code == 200
    data = r.json()
    print(f"✅ dependency-004 score → {data['total_score']}")
    print(f"   Feedback: {data['feedback']}")


def test_scenarios_list():
    """Verify the /scenarios endpoint."""
    r = httpx.get(f"{BASE}/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 15
    print(f"✅ /scenarios → {data['total']} scenarios listed")


def main():
    print("=" * 60)
    print("  OptiMaintainer Integration Tests")
    print("=" * 60)

    # Health & Reset
    test_health()
    test_reset()

    # Triage tests
    test_triage_perfect()
    test_triage_partial()

    # Security tests
    test_security_perfect()
    test_security_with_false_positive()

    # Dependency test
    test_dependency_perfect()

    # Scenarios endpoint
    test_scenarios_list()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except httpx.ConnectError:
        print("❌ Cannot connect to server. Is it running on localhost:8000?")
        sys.exit(1)
