"""OpenEnv Graders for OptiMaintainer.

Each grader returns a score between 0.0 and 1.0.
Supports partial credit (not binary-only).

Grading formulas:
- Triage: avg(category, severity, routing, decision)
- Security: 0.6 base + 0.4 keyword, with FP penalty
- Dependency: 0.2 version + 0.4 breaking + 0.4 migration

Note: The actual grader implementations are in the root graders.py file.
This module re-exports them for OpenEnv directory structure compliance.
"""

import sys
from pathlib import Path

parent = Path(__file__).resolve().parent.parent
if str(parent) not in sys.path:
    sys.path.insert(0, str(parent))

import importlib.util
spec = importlib.util.spec_from_file_location("root_graders", parent / "graders.py")
root_graders = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_graders)

grade_triage = root_graders.grade_triage
grade_security_audit = root_graders.grade_security_audit
grade_dependency = root_graders.grade_dependency
GRADER_MAP = root_graders.GRADER_MAP

__all__ = ["grade_triage", "grade_security_audit", "grade_dependency", "GRADER_MAP"]
