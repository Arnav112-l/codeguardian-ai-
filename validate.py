"""Quick validation script for OptiMaintainer."""
import httpx
import sys

B = "http://localhost:8000"

def run():
    # Health
    r = httpx.get(f"{B}/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    print("HEALTH:", r.json())

    # Reset
    r = httpx.post(f"{B}/reset")
    assert r.status_code == 200
    print("RESET:", r.json()["total_scenarios"], "scenarios")

    # Triage perfect
    r = httpx.post(f"{B}/step", json={
        "action_type": "triage",
        "scenario_id": "triage-001",
        "payload": {
            "category": "bug",
            "severity": "high",
            "assignee": "oncall:distributed",
            "decision": "stop"
        }
    })
    d = r.json()
    print(f"TRIAGE-001 (perfect): score={d['total_score']}")
    assert d["total_score"] == 1.0

    # Triage partial (severity 1 off)
    r = httpx.post(f"{B}/step", json={
        "action_type": "triage",
        "scenario_id": "triage-002",
        "payload": {
            "category": "feature",
            "severity": "high",
            "assignee": "oncall:pt2",
            "decision": "continue"
        }
    })
    d = r.json()
    print(f"TRIAGE-002 (partial): score={d['total_score']}")
    assert d["total_score"] == 0.875

    # Security perfect
    r = httpx.post(f"{B}/step", json={
        "action_type": "security",
        "scenario_id": "security-001",
        "payload": {
            "findings": [{
                "cwe_id": "CWE-89",
                "line_number": 2,
                "fix_description": "Use parameterized queries with bound parameters"
            }]
        }
    })
    d = r.json()
    print(f"SECURITY-001 (perfect): score={d['total_score']}")
    assert d["total_score"] == 1.0

    # Security with false positive
    r = httpx.post(f"{B}/step", json={
        "action_type": "security",
        "scenario_id": "security-002",
        "payload": {
            "findings": [
                {"cwe_id": "CWE-79", "line_number": 2, "fix_description": "Sanitize output with bleach"},
                {"cwe_id": "CWE-502", "line_number": 99, "fix_description": "Not a real vuln"}
            ]
        }
    })
    d = r.json()
    print(f"SECURITY-002 (with FP): score={d['total_score']}")
    assert d["total_score"] == 0.95

    # Dependency
    r = httpx.post(f"{B}/step", json={
        "action_type": "dependency",
        "scenario_id": "dependency-004",
        "payload": {
            "updates": [{
                "package": "requests",
                "from_version": "2.31.0",
                "to_version": "2.32.3",
                "is_breaking": False,
                "migration_notes": "This is a bugfix patch update for session handling and certificate verification"
            }]
        }
    })
    d = r.json()
    print(f"DEPENDENCY-004: score={d['total_score']}")
    print(f"  Feedback: {d['feedback']}")

    # Scenarios
    r = httpx.get(f"{B}/scenarios")
    print(f"SCENARIOS: {r.json()['total']} total")

    print("\n" + "=" * 50)
    print("  ALL VALIDATIONS PASSED")
    print("=" * 50)

if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"FAILED: {e}")
        sys.exit(1)
    except httpx.ConnectError:
        print("ERROR: Server not running on localhost:8000")
        sys.exit(1)
