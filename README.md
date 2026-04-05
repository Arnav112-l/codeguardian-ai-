# 🔧 OptiMaintainer

**Production-grade OpenEnv environment for grading AI agents on open-source repository maintenance.**

Built for the META HACKATHON — grades agents across three tracks: Issue Triage, Security Audit, and Dependency Management.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/health
# → {"status": "ok"}
```

### Docker

```bash
docker build -t optimaintainer .
docker run -p 8000:8000 optimaintainer
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reset` | Reset environment for a new episode |
| `POST` | `/step` | Submit an action, receive graded observation |
| `GET` | `/health` | Health check → `{"status": "ok"}` |
| `GET` | `/scenarios` | List all 15 scenarios with context |
| `GET` | `/state` | Current episode progress & scores |

---

## Action Space

Agents interact with the environment by sending `POST /step` with the following action types:

### 1. Triage (`action_type: "triage"`)

Classify and route repository issues.

```json
{
  "action_type": "triage",
  "scenario_id": "triage-001",
  "payload": {
    "category": "bug",
    "severity": "high",
    "assignee": "oncall:distributed",
    "decision": "stop"
  }
}
```

| Field | Type | Values |
|-------|------|--------|
| `category` | string | `"bug"`, `"feature"`, `"performance"`, `"documentation"` |
| `severity` | enum | `"low"`, `"medium"`, `"high"`, `"critical"` |
| `assignee` | string | oncall identifier (e.g., `"oncall:distributed"`) |
| `decision` | enum | `"stop"` (escalation halts) or `"continue"` (escalation proceeds) |

### 2. Security Audit (`action_type: "security"`)

Detect vulnerabilities in code snippets.

```json
{
  "action_type": "security",
  "scenario_id": "security-001",
  "payload": {
    "findings": [
      {
        "cwe_id": "CWE-89",
        "line_number": 2,
        "fix_description": "Use parameterized queries with bound parameters"
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `findings[].cwe_id` | string | CWE identifier (e.g., `"CWE-89"`) |
| `findings[].line_number` | int | Source line of the vulnerability (≥1) |
| `findings[].fix_description` | string | Recommended remediation |

### 3. Dependency Update (`action_type: "dependency"`)

Propose package version updates with migration analysis.

```json
{
  "action_type": "dependency",
  "scenario_id": "dependency-001",
  "payload": {
    "updates": [
      {
        "package": "numpy",
        "from_version": "1.24.4",
        "to_version": "2.0.0",
        "is_breaking": true,
        "migration_notes": "The deprecated API functions have been removed. int64 is now the default dtype. numpy.distutils has been removed in favor of meson."
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `updates[].package` | string | Package name |
| `updates[].from_version` | string | Current version |
| `updates[].to_version` | string | Target version |
| `updates[].is_breaking` | bool | Whether the update has breaking changes |
| `updates[].migration_notes` | string | Free-text migration instructions |

---

## Observation Space

Every `/step` call returns a structured **Observation**:

```json
{
  "scenario_id": "triage-001",
  "action_type": "triage",
  "total_score": 0.875,
  "sub_scores": [
    {"name": "category", "score": 1.0, "feedback": "Correct category: 'bug'"},
    {"name": "severity", "score": 0.5, "feedback": "Severity one level off (expected medium, got high)"},
    {"name": "routing", "score": 1.0, "feedback": "Exact assignee match: oncall:distributed"},
    {"name": "decision", "score": 1.0, "feedback": "Correct decision: stop"}
  ],
  "feedback": "[category] Correct | [severity] One level off | [routing] Exact | [decision] Correct",
  "done": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_score` | float | Overall score [0.0, 1.0] |
| `sub_scores` | array | Breakdown by grading dimension |
| `feedback` | string | Human-readable explanation |
| `done` | bool | `true` when all 15 scenarios are complete |

---

## Scoring Formulas
### Triage (avg of Cat, Sev, Routing)
- **Category**: 1.0 exact, 0.0 wrong
- **Severity**: 1.0 exact, 0.5 adjacent, 0.0 otherwise (ordinal: low=0, medium=1, high=2, critical=3)
- **Routing**: 1.0 exact assignee, 0.5 correct domain, 0.0 wrong
- **Decision**: 1.0 correct, 0.0 wrong (logged as sub-score but not in total average)

### Security (0.6 Base + 0.4 Quality)
- **Match**: CWE must match exactly and line within ±2 range.
- **Scoring**: 0.6 base for match + 0.4 bonus for keyword overlap in fix description.
- **Penalty**: 0.7x multiplier applied if a CRITICAL or BLOCKER vulnerability is missed.
- **False Positives**: -0.05 deduction per reported finding that is not in ground truth (max -0.2).

### Dependency Updater
- **Version**: 0.2 weight (exact version match)
- **Breaking Recall**: 0.4 weight (flagging breaking changes)
- **Migration Quality**: 0.4 weight (keyword overlap against reference)
- **Zero-LLM Loop**: Grading uses purely programmatic string/keyword logic.

---

## Scenario Bank

15 scenarios (5 per track) stored in `scenario_bank.json`, covering real-world PyTorch/HuggingFace maintenance tasks:

| Track | Scenarios | Examples |
|-------|-----------|----------|
| Triage | 5 | DDP memory leak, torch.compile feature request, checkpoint corruption |
| Security | 5 | SQL injection, XSS, unsafe deserialization, path traversal, SSRF |
| Dependency | 5 | NumPy 2.0, Pydantic v2, Flask 3.0, requests patch, transformers 4.40 |

---

## Project Structure

```
Meta/
├── models.py              # Pydantic schemas (Action, Observation)
├── scenario_bank.json     # 15 test scenarios with reference answers
├── requirements.txt       # Pinned dependencies (== only)
├── Dockerfile             # python:3.11-slim, curl HEALTHCHECK
├── .dockerignore
├── server/
│   ├── __init__.py
│   ├── app.py             # FastAPI: /reset, /step, /health
│   ├── triage_grader.py   # Issue classification grader
│   ├── security_grader.py # Vulnerability detection grader
│   └── dependency_grader.py # Package update grader
├── test_audit.py          # Comprehensive rubric compliance tests
├── validate.py            # Quick validation script
└── README.md
```

---

## Running the Audit

```bash
# Start server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# In another terminal
python test_audit.py
# → 🏆 100% COMPLIANCE — READY FOR SUBMISSION
```
