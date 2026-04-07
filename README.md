---
title: CodeGuardian AI
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
tags:
  - openenv
---

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

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

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
