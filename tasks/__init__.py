"""OpenEnv Tasks for OptiMaintainer.

Three tracks:
- triage: Issue classification and routing
- security: Vulnerability detection (CWE-based)
- dependency: Package upgrade recommendations
"""

TASK_REGISTRY = {
    "task_triage": {
        "id": "task_triage",
        "difficulty": "easy",
        "description": "Triage incoming bug/feature/docs/question tickets",
        "scenarios": 5,
    },
    "task_security_audit": {
        "id": "task_security_audit",
        "difficulty": "medium",
        "description": "Identify CWE vulnerabilities in Python code snippets",
        "scenarios": 5,
    },
    "task_dependency_update": {
        "id": "task_dependency_update",
        "difficulty": "hard",
        "description": "Recommend safe dependency version upgrades with migration plan",
        "scenarios": 5,
    },
}

__all__ = ["TASK_REGISTRY"]
