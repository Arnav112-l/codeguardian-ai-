"""
OptiMaintainer — FastAPI Application

Endpoints:
  POST /reset       — Reset the environment to a fresh episode
  POST /step        — Submit an action, receive graded observation
  GET  /health      — Health check (returns {"status": "ok"})
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Ensure project root is on sys.path for imports ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models import Action, ActionType, EnvState, Observation
from server import triage_grader, security_grader, dependency_grader

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("optimaintainer")

# ─────────────────────────────────────────────
#  Load scenario bank
# ─────────────────────────────────────────────
SCENARIO_BANK_PATH = PROJECT_ROOT / "scenario_bank.json"

def _load_scenarios() -> List[Dict[str, Any]]:
    with open(SCENARIO_BANK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]

SCENARIOS: List[Dict[str, Any]] = _load_scenarios()
SCENARIO_MAP: Dict[str, Dict[str, Any]] = {s["id"]: s for s in SCENARIOS}

logger.info("Loaded %d scenarios from %s", len(SCENARIOS), SCENARIO_BANK_PATH)

# ─────────────────────────────────────────────
#  Grader dispatch
# ─────────────────────────────────────────────
_GRADERS = {
    "triage": triage_grader,
    "security": security_grader,
    "dependency": dependency_grader,
}

# ─────────────────────────────────────────────
#  FastAPI app
# ─────────────────────────────────────────────
app = FastAPI(
    title="OptiMaintainer",
    description="OpenEnv grading environment for AI repo-maintenance agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Episode state (in-memory, single-agent for now) ──
_state: EnvState = EnvState()


# ─────────────────────────────────────────────
#  Request / Response DTOs
# ─────────────────────────────────────────────

class ResetResponse(BaseModel):
    message: str
    total_scenarios: int
    scenario_ids: List[str]


class StepRequest(BaseModel):
    action_type: str
    scenario_id: str
    payload: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str


# ─────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────

@app.post("/reset", response_model=ResetResponse)
async def reset_environment():
    """Reset the grading environment to the beginning of a new episode."""
    global _state
    _state = EnvState()
    logger.info("Environment reset — %d scenarios available", len(SCENARIOS))
    return ResetResponse(
        message="Environment reset successfully. Submit actions via /step.",
        total_scenarios=len(SCENARIOS),
        scenario_ids=[s["id"] for s in SCENARIOS],
    )


@app.post("/step", response_model=Observation)
async def step(request: StepRequest):
    """
    Accept an agent action, grade it, and return the observation.

    The action is routed to the appropriate grader based on `action_type`.
    """
    if _state.episode_done:
        raise HTTPException(
            status_code=400,
            detail="Episode is done. Call /reset to start a new one.",
        )

    # Validate scenario exists
    scenario = SCENARIO_MAP.get(request.scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario_id: '{request.scenario_id}'. "
                   f"Valid IDs: {list(SCENARIO_MAP.keys())}",
        )

    # Prevent duplicate submissions
    if request.scenario_id in _state.completed_scenarios:
        raise HTTPException(
            status_code=409,
            detail=f"Scenario '{request.scenario_id}' already submitted.",
        )

    # Validate action_type matches scenario type
    scenario_type = scenario["type"]
    if request.action_type != scenario_type:
        raise HTTPException(
            status_code=422,
            detail=f"Action type '{request.action_type}' does not match "
                   f"scenario type '{scenario_type}' for {request.scenario_id}.",
        )

    # Build Action model
    try:
        action = Action(
            action_type=ActionType(request.action_type),
            scenario_id=request.scenario_id,
            payload=request.payload,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid action: {e}")

    # Route to grader
    grader = _GRADERS.get(scenario_type)
    if grader is None:
        raise HTTPException(
            status_code=500,
            detail=f"No grader registered for type '{scenario_type}'",
        )

    reference = scenario["reference"]
    observation: Observation = grader.grade(action, reference)

    # Update state
    _state.completed_scenarios.append(request.scenario_id)
    _state.scores[request.scenario_id] = observation.total_score
    _state.current_scenario_idx += 1

    # Check if episode is complete
    if len(_state.completed_scenarios) >= len(SCENARIOS):
        observation.done = True
        _state.episode_done = True
        avg_score = sum(_state.scores.values()) / len(_state.scores)
        observation.feedback += (
            f" | 🏁 Episode complete! Average score: {avg_score:.4f} "
            f"across {len(_state.scores)} scenarios."
        )

    logger.info(
        "Graded %s | scenario=%s | score=%.4f | done=%s",
        request.action_type,
        request.scenario_id,
        observation.total_score,
        observation.done,
    )

    return observation


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Docker HEALTHCHECK and monitoring."""
    return HealthResponse(status="ok")


@app.get("/scenarios")
async def list_scenarios():
    """List all available scenarios (for agent bootstrapping)."""
    return {
        "total": len(SCENARIOS),
        "scenarios": [
            {
                "id": s["id"],
                "type": s["type"],
                "description": s["description"],
                "context": s.get("context", {}),
            }
            for s in SCENARIOS
        ],
    }


@app.get("/state")
async def get_state():
    """Return the current episode state (for debugging)."""
    return {
        "completed": _state.completed_scenarios,
        "scores": _state.scores,
        "remaining": len(SCENARIOS) - len(_state.completed_scenarios),
        "episode_done": _state.episode_done,
        "average_score": (
            sum(_state.scores.values()) / len(_state.scores)
            if _state.scores
            else None
        ),
    }
