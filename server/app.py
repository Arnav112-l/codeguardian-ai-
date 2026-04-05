from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- PROJECT ROOT SETUP ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- GRADER & MODELS IMPORTS ---
from models import ActionType, EnvState, Observation, model_validate_action
from graders import GRADER_MAP

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("optimaintainer")

# --- DATA ---
SCENARIO_BANK_PATH = PROJECT_ROOT / "scenario_bank.json"
def _load_scenarios() -> List[Dict[str, Any]]:
    with open(SCENARIO_BANK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]

SCENARIOS = _load_scenarios()
SCENARIO_MAP = {s["id"]: s for s in SCENARIOS}

# --- APP ---
app = FastAPI(title="OptiMaintainer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: EnvState = EnvState()

# --- Request Models ---
class StepRequest(BaseModel):
    action_type: str
    scenario_id: str
    payload: Dict[str, Any]

# --- ENDPOINTS ---
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/reset")
async def reset():
    global _state
    _state = EnvState()
    return {
        "message": "Reset done",
        "total_scenarios": len(SCENARIOS),
        "scenario_ids": [s["id"] for s in SCENARIOS]
    }

@app.post("/step")
async def step(req: StepRequest):
    global _state
    
    # 1. Validation
    scenario = SCENARIO_MAP.get(req.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    
    if req.scenario_id in _state.completed_scenarios:
        raise HTTPException(status_code=409, detail="Duplicate submission")
        
    if req.action_type != scenario["type"]:
        raise HTTPException(status_code=422, detail="Type mismatch")

    # 2. Map Task ID for Action Validator
    # Root models.py model_validate_action expects task_triage, etc.
    task_id = "task_" + req.action_type
    if req.action_type == "dependency":
        task_id = "task_dependency_update"
    
    try:
        action_payload = model_validate_action(req.payload, task_id)
    except Exception as e:
        logger.error(f"Validation failed for {task_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    # 3. Grade
    grader = GRADER_MAP.get(req.action_type)
    if not grader:
        raise HTTPException(status_code=500, detail="Grader missing")
    
    reference = scenario["reference"]
    reward = grader(action_payload, reference)

    # 4. Convert Sub-scores to list format for test_audit.py
    api_sub_scores = []
    for name, score in reward.sub_scores.items():
        api_sub_scores.append({"name": name, "score": score})

    # 6. Update State
    _state.completed_scenarios.append(req.scenario_id)
    _state.scores[req.scenario_id] = reward.total_score
    
    done = False
    if len(_state.completed_scenarios) >= len(SCENARIOS):
        done = True

    return {
        "scenario_id": req.scenario_id,
        "action_type": req.action_type,
        "total_score": float(reward.total_score),
        "sub_scores": api_sub_scores,
        "feedback": reward.feedback,
        "done": done
    }

@app.get("/state")
async def get_state():
    return {
        "episode_id": id(_state),
        "step_count": len(_state.completed_scenarios),
        "scores": _state.scores,
        "episode_done": _state.episode_done
    }
