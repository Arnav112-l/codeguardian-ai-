
<div align="center">

# 🛡️ CodeGuardian AI

### Production-Grade OpenEnv Environment for AI Agent Evaluation

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-brightgreen)](https://openenv.dev)
[![HuggingFace Spaces](https://img.shields.io/badge/🤗%20HuggingFace-Spaces-blue)](https://huggingface.co/spaces/zeus1205/codeguardian-ai)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Benchmark AI agents on real-world open-source maintenance tasks:**  
**Issue Triage • Security Auditing • Dependency Management**

[🚀 Live Demo](https://zeus1205-codeguardian-ai.hf.space) • [📖 API Docs](https://zeus1205-codeguardian-ai.hf.space/docs) • [🎮 Interactive Playground](https://zeus1205-codeguardian-ai.hf.space/demo)

</div>

---

## 🎯 Overview

**CodeGuardian AI** is an OpenEnv-compliant evaluation environment that benchmarks LLM-powered coding agents on three critical open-source maintenance tasks. It provides deterministic grading with partial-credit scoring, enabling reproducible and fair comparisons between AI systems.

### Why CodeGuardian AI?

Open-source maintainers are overwhelmed with:
- 📋 **Hundreds of issues** requiring accurate triage and routing
- 🔒 **Security vulnerabilities** hidden in codebases  
- 📦 **Dependency updates** with complex breaking changes

This environment tests whether AI agents can reliably assist with these tasks, using real-world scenarios from PyTorch and HuggingFace ecosystems.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CodeGuardian AI                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐     ┌──────────────┐               │
│   │   AI Agent   │────▶│  FastAPI     │────▶│  Environment │               │
│   │   (LLM)      │◀────│  Server      │◀────│  State       │               │
│   └──────────────┘     └──────────────┘      └──────────────┘               │
│          │                    │                    │                        │
│          │              ┌─────┴─────┐              │                        │
│          │              ▼           ▼              │                        │
│          │     ┌────────────┐ ┌──────────┐         │                        │
│          │     │  Graders   │ │ Scenario │         │                        │
│          │     │ (3 types)  │ │   Bank   │         │                        │
│          │     └────────────┘ └──────────┘         │                        │
│          │              │           │              │                        │
│          ▼              ▼           ▼              ▼                        │
│    ┌─────────────────────────────────────────────────────────────┐          │
│    │                     Episode Flow                            │          │
│    │  /reset → Get 15 scenarios → /step (submit action) → Score  │          │
│    │           ↑                           │                     │          │
│    │           └───────────────────────────┘ (repeat 15x)        │          │
│    └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   Task Tracks:                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│   │   TRIAGE    │  │  SECURITY   │  │ DEPENDENCY  │                         │
│   │   (Easy)    │  │  (Medium)   │  │   (Hard)    │                         │
│   │  5 scenarios│  │  5 scenarios│  │  5 scenarios│                         │
│   └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🎯 3 Task Tracks** | Triage, Security Audit, Dependency Management |
| **📊 15 Scenarios** | 5 scenarios per track, covering edge cases |
| **⚖️ Partial Credit** | Scores from 0.0 to 1.0 with nuanced grading |
| **🔄 Deterministic** | Zero-LLM grading logic for reproducibility |
| **🐳 Docker Ready** | One-command deployment with health checks |
| **🌐 OpenEnv Spec** | Full compliance with hackathon requirements |

---

## 🚀 Quick Start

### Option 1: Use Live API

```bash
# Test the live environment
curl https://zeus1205-codeguardian-ai.hf.space/reset
curl https://zeus1205-codeguardian-ai.hf.space/state
```

### Option 2: Run Locally

```bash
# Clone repository
git clone https://github.com/Arnav112-l/codeguardian-ai-.git
cd codeguardian-ai-

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Verify
curl http://localhost:7860/health
# → {"status": "ok"}
```

### Option 3: Docker

```bash
docker build -t codeguardian-ai .
docker run -p 7860:7860 codeguardian-ai
```

---

## 📡 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Environment info and available endpoints |
| `GET/POST` | `/reset` | Reset environment for new episode |
| `GET` | `/state` | Current episode progress and scores |
| `POST` | `/step` | Submit action, receive graded observation |
| `GET` | `/health` | Health check |
| `GET` | `/demo` | Interactive web interface |
| `GET` | `/docs` | OpenAPI documentation |

### Example: Complete Episode Flow

```python
import httpx

BASE_URL = "https://zeus1205-codeguardian-ai.hf.space"

# 1. Reset environment
reset = httpx.get(f"{BASE_URL}/reset").json()
print(f"Scenarios: {reset['scenario_ids']}")

# 2. Submit action
action = {
    "action_type": "triage",
    "scenario_id": "triage-001",
    "payload": {
        "category": "bug",
        "severity": "high",
        "assignee": "oncall:distributed",
        "decision": "stop"
    }
}
result = httpx.post(f"{BASE_URL}/step", json=action).json()
print(f"Score: {result['total_score']}")  # → 1.0

# 3. Check state
state = httpx.get(f"{BASE_URL}/state").json()
print(f"Completed: {state['step_count']}/15")
```

---

## 🎮 Task Tracks

### 1. Issue Triage (Easy)
Classify and route repository issues to appropriate teams.

```json
{
  "action_type": "triage",
  "scenario_id": "triage-001",
  "payload": {
    "category": "bug",           // bug | feature | docs | question | performance
    "severity": "high",          // low | medium | high | critical
    "assignee": "oncall:distributed",
    "decision": "stop"           // stop | continue
  }
}
```

**Scoring:**
- Category: 1.0 exact, 0.0 wrong
- Severity: 1.0 exact, 0.5 adjacent, 0.0 otherwise
- Routing: 1.0 exact, 0.5 correct domain
- Decision: 1.0 correct, 0.0 wrong

### 2. Security Audit (Medium)
Detect CWE vulnerabilities in Python code snippets.

```json
{
  "action_type": "security",
  "scenario_id": "security-001",
  "payload": {
    "findings": [{
      "cwe_id": "CWE-89",
      "line_number": 2,
      "severity": "critical",
      "fix_description": "Use parameterized queries"
    }]
  }
}
```

**Scoring:**
- Base: 0.6 for correct CWE + line (±2)
- Bonus: +0.4 for relevant fix keywords
- Penalty: 0.7x if critical vuln missed
- FP Penalty: -0.05 per false positive (max -0.2)

### 3. Dependency Update (Hard)
Recommend safe package upgrades with migration plans.

```json
{
  "action_type": "dependency",
  "scenario_id": "dependency-001",
  "payload": {
    "updates": [{
      "package": "numpy",
      "from_version": "1.24.4",
      "to_version": "2.0.0",
      "is_breaking": true,
      "migration_notes": "int64 default dtype, distutils removed"
    }]
  }
}
```

**Scoring:**
- Version: 0.2 weight (exact match)
- Breaking: 0.4 weight (correct flag)
- Migration: 0.4 weight (keyword overlap)

---

## 📋 Complete Action Schema Examples

<details>
<summary><b>🔽 Click to expand full request/response examples</b></summary>

### Triage Action - Full Example

**Request:**
```json
POST /step
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

**Response:**
```json
{
  "scenario_id": "triage-001",
  "task_id": "task_triage",
  "action_type": "triage",
  "total_score": 0.875,
  "sub_scores": [
    {"name": "category", "score": 1.0},
    {"name": "severity", "score": 0.5},
    {"name": "routing", "score": 1.0},
    {"name": "decision", "score": 1.0}
  ],
  "feedback": "cat=1.0, sev=0.5, routing=1.0, dec=1.0",
  "done": false
}
```

### Security Audit Action - Full Example

**Request:**
```json
POST /step
{
  "action_type": "security",
  "scenario_id": "security-001",
  "payload": {
    "findings": [
      {
        "cwe_id": "CWE-89",
        "line_number": 2,
        "severity": "critical",
        "fix_description": "Use parameterized queries with bound parameters to prevent SQL injection"
      },
      {
        "cwe_id": "CWE-79",
        "line_number": 8,
        "severity": "high",
        "fix_description": "Escape user input with html.escape() or use innerText instead of innerHTML"
      }
    ]
  }
}
```

**Response:**
```json
{
  "scenario_id": "security-001",
  "task_id": "task_security_audit",
  "action_type": "security",
  "total_score": 0.85,
  "sub_scores": [
    {"name": "finding_CWE-89_2", "score": 1.0},
    {"name": "finding_CWE-79_8", "score": 0.6},
    {"name": "recall_penalty", "score": 1.0},
    {"name": "fp_penalty", "score": 1.0}
  ],
  "feedback": "Found 2/2 vulns with 0 FPs.",
  "done": false
}
```

### Dependency Update Action - Full Example

**Request:**
```json
POST /step
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
        "migration_notes": "The deprecated API functions have been removed. int64 is now the default integer dtype. numpy.distutils has been removed in favor of meson build system."
      },
      {
        "package": "pydantic",
        "from_version": "1.10.0",
        "to_version": "2.0.0",
        "is_breaking": true,
        "migration_notes": "Use model_validate instead of parse_obj. ConfigDict replaces class Config. Field constraints use Annotated types."
      }
    ]
  }
}
```

**Response:**
```json
{
  "scenario_id": "dependency-001",
  "task_id": "task_dependency_update",
  "action_type": "dependency",
  "total_score": 0.92,
  "sub_scores": [
    {"name": "version", "score": 1.0},
    {"name": "breaking_recall", "score": 1.0},
    {"name": "migration", "score": 0.8}
  ],
  "feedback": "v=1.00, b=1.00, m=0.80",
  "done": false
}
```

### Reset Endpoint Response

```json
GET /reset
{
  "message": "Environment reset",
  "scenario_ids": [
    "triage-001", "triage-002", "triage-003", "triage-004", "triage-005",
    "security-001", "security-002", "security-003", "security-004", "security-005",
    "dependency-001", "dependency-002", "dependency-003", "dependency-004", "dependency-005"
  ],
  "scenarios": [...],
  "total_scenarios": 15
}
```

### State Endpoint Response

```json
GET /state
{
  "episode_id": "ep_abc123",
  "task_id": "task_triage",
  "step_count": 5,
  "current_scenario_id": "security-001",
  "cumulative_reward": 4.25,
  "completed_scenarios": ["triage-001", "triage-002", "triage-003", "triage-004", "triage-005"],
  "scores": {
    "triage-001": 1.0,
    "triage-002": 0.75,
    "triage-003": 0.875,
    "triage-004": 0.625,
    "triage-005": 1.0
  }
}
```

</details>

---

## 📊 Scenario Bank

15 curated scenarios from real PyTorch/HuggingFace maintenance:

| Track | Count | Examples |
|-------|-------|----------|
| **Triage** | 5 | DDP memory leak, torch.compile feature, checkpoint corruption |
| **Security** | 5 | SQL injection, XSS, pickle deserialization, path traversal, SSRF |
| **Dependency** | 5 | NumPy 2.0, Pydantic v2, Flask 3.0, transformers 4.40 |

---

## 📈 Baseline Scores

Random agent performance (baseline):

| Task | Avg Score | Target |
|------|-----------|--------|
| Triage | 0.38 | 0.75 |
| Security Audit | 0.20 | 0.55 |
| Dependency Update | 0.30 | 0.35 |

Run baseline yourself:
```bash
python inference.py --mock
```

---

## 🏗️ Project Structure

```
codeguardian-ai/
├── server/
│   ├── app.py              # FastAPI application
│   └── __init__.py
├── graders/
│   └── __init__.py         # Grader exports
├── tasks/
│   └── __init__.py         # Task registry
├── tests/
│   └── test_models.py      # Unit tests
├── models.py               # Pydantic schemas
├── graders.py              # Deterministic grading logic
├── environment.py          # Environment state management
├── inference.py            # OpenEnv inference script
├── scenario_bank.json      # 15 test scenarios
├── openenv.yaml            # OpenEnv configuration
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── README.md
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `Qwen/Qwen2.5-72B-Instruct` |
| `HF_TOKEN` | HuggingFace API token | Required for live runs |
| `OPENENV_URL` | Grading server URL | `https://zeus1205-codeguardian-ai.hf.space` |

### OpenEnv Configuration (`openenv.yaml`)

```yaml
name: "codeguardian-ai"
version: "1.0.0"
type: coding_env
runtime: docker
app_port: 7860
reward_range: [0.0, 1.0]
tags: [openenv, coding, security, devtools]
```

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run audit compliance
python test_audit.py

# Run integration tests
python test_integration.py
```

---

## 📦 Deployment

### HuggingFace Spaces

The environment is deployed at:  
**https://zeus1205-codeguardian-ai.hf.space**

### Self-Hosted

```bash
# Build and run
docker build -t codeguardian-ai .
docker run -d -p 7860:7860 --name codeguardian codeguardian-ai

# Verify
curl http://localhost:7860/health
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request



## 🙏 Acknowledgments

- **META x Scaler Hackathon** - Competition framework
- **OpenEnv** - Evaluation specification
- **HuggingFace** - Hosting infrastructure
- **FastAPI** - API framework

---

<div align="center">

**Built with ❤️ for the AI Agent Evaluation Community**

[⭐ Star this repo](https://github.com/Arnav112-l/codeguardian-ai-) if you find it useful!

</div>
