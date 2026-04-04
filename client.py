"""
OptiMaintainer — EnvClient for agent-side usage.

This module provides the client class that agents use to interact with the
OptiMaintainer grading environment, following the OpenEnv EnvClient pattern.

Usage (async):
    async with OptiMaintainerEnv(base_url="http://localhost:8000") as client:
        result = await client.reset()
        result = await client.step(TriageAction(...))

Usage (sync):
    with OptiMaintainerEnv(base_url="http://localhost:8000").sync() as client:
        result = client.reset()
        result = client.step(TriageAction(...))
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from models import Action, ActionType, Observation


class StepResult:
    """Result of a step call, combining observation and reward."""

    def __init__(self, observation: Observation, reward: float, done: bool):
        self.observation = observation
        self.reward = reward
        self.done = done

    def __repr__(self) -> str:
        return (
            f"StepResult(score={self.reward:.4f}, "
            f"done={self.done}, "
            f"scenario={self.observation.scenario_id})"
        )


class ResetResult:
    """Result of a reset call."""

    def __init__(self, message: str, total_scenarios: int, scenario_ids: list):
        self.message = message
        self.total_scenarios = total_scenarios
        self.scenario_ids = scenario_ids

    def __repr__(self) -> str:
        return f"ResetResult(scenarios={self.total_scenarios})"


class OptiMaintainerEnv:
    """
    OpenEnv-compatible client for the OptiMaintainer grading environment.

    Implements the standard OpenEnv interface:
      - reset()  → ResetResult
      - step()   → StepResult (observation + reward + done)
      - state()  → dict with episode progress

    Parameters
    ----------
    base_url : str
        URL of the running OptiMaintainer server (e.g. http://localhost:8000)
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    # ── Async context manager ──

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    # ── Core API (async) ──

    async def reset(self) -> ResetResult:
        """Reset the environment for a new episode."""
        r = await self._client.post("/reset")
        r.raise_for_status()
        d = r.json()
        return ResetResult(
            message=d["message"],
            total_scenarios=d["total_scenarios"],
            scenario_ids=d["scenario_ids"],
        )

    async def step(
        self,
        action_type: str,
        scenario_id: str,
        payload: Dict[str, Any],
    ) -> StepResult:
        """Submit an action and receive a graded observation."""
        r = await self._client.post("/step", json={
            "action_type": action_type,
            "scenario_id": scenario_id,
            "payload": payload,
        })
        r.raise_for_status()
        d = r.json()
        obs = Observation(**d)
        return StepResult(
            observation=obs,
            reward=obs.total_score,
            done=obs.done,
        )

    async def state(self) -> dict:
        """Get the current episode state."""
        r = await self._client.get("/state")
        r.raise_for_status()
        return r.json()

    async def scenarios(self) -> dict:
        """List all available scenarios."""
        r = await self._client.get("/scenarios")
        r.raise_for_status()
        return r.json()

    # ── Sync wrapper ──

    def sync(self) -> SyncOptiMaintainerEnv:
        """Return a synchronous wrapper for this client."""
        return SyncOptiMaintainerEnv(self.base_url)


class SyncOptiMaintainerEnv:
    """Synchronous wrapper for OptiMaintainerEnv."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.Client] = None

    def __enter__(self):
        self._client = httpx.Client(base_url=self.base_url, timeout=30.0)
        return self

    def __exit__(self, *args):
        if self._client:
            self._client.close()

    def reset(self) -> ResetResult:
        r = self._client.post("/reset")
        r.raise_for_status()
        d = r.json()
        return ResetResult(
            message=d["message"],
            total_scenarios=d["total_scenarios"],
            scenario_ids=d["scenario_ids"],
        )

    def step(
        self,
        action_type: str,
        scenario_id: str,
        payload: Dict[str, Any],
    ) -> StepResult:
        r = self._client.post("/step", json={
            "action_type": action_type,
            "scenario_id": scenario_id,
            "payload": payload,
        })
        r.raise_for_status()
        d = r.json()
        obs = Observation(**d)
        return StepResult(
            observation=obs,
            reward=obs.total_score,
            done=obs.done,
        )

    def state(self) -> dict:
        r = self._client.get("/state")
        r.raise_for_status()
        return r.json()

    def scenarios(self) -> dict:
        r = self._client.get("/scenarios")
        r.raise_for_status()
        return r.json()
