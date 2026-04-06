import json
from pathlib import Path
import uuid
from typing import Any

from graders import GRADER_MAP
from models import (
    Action,
    DependencyAction,
    Observation,
    Reward,
    SecurityAuditAction,
    State,
    TriageAction,
)

class CodingEnvironment:
    def __init__(self, scenario_bank_path: str = "scenario_bank.json") -> None:
        with open(scenario_bank_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scenarios = data["scenarios"]
        # Map by type: list of scenarios
        self.scenario_bank = {}
        for s in scenarios:
            t = s["type"]
            if t not in self.scenario_bank:
                self.scenario_bank[t] = []
            self.scenario_bank[t].append(s)
            
        self.episode_id: str | None = None
        self.current_task_id: str | None = None
        self.current_scenario_id: str | None = None
        self._current_scenario: dict[str, Any] | None = None
        self.step_count: int = 0
        self.cumulative_reward: float = 0.0

    def reset(self, task_id: str, scenario_index: int) -> Observation:
        # Map task IDs: task_triage -> triage, etc.
        lookup_id = task_id.replace("task_", "").replace("_update", "").replace("_audit", "")
        if lookup_id not in self.scenario_bank:
            raise ValueError(f"Unknown task_id: {task_id} (lookup={lookup_id})")

        scenarios = self.scenario_bank[lookup_id]
        if scenario_index < 0 or scenario_index >= len(scenarios):
            raise IndexError(
                f"Scenario index out of range for {task_id}: {scenario_index}"
            )

        scenario = scenarios[scenario_index]
        self.episode_id = str(uuid.uuid4())
        self.current_task_id = task_id
        self.current_scenario_id = scenario["id"]
        self._current_scenario = scenario
        self.step_count = 0
        self.cumulative_reward = 0.0

        return self._build_observation(step_number=0)

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict[str, Any]]:
        if self.current_task_id is None or self._current_scenario is None:
            raise RuntimeError("Environment is not initialized. Call reset() first.")

        # Task ID to model mapping
        task_norm = self.current_task_id.lower().replace("task_", "").replace("_update", "").replace("_audit", "")
        
        expected_action = {
            "triage": TriageAction,
            "security": SecurityAuditAction,
            "dependency": DependencyAction,
        }.get(task_norm)

        if expected_action is None:
            raise ValueError(f"No action contract defined for task: {self.current_task_id}")

        if not isinstance(action, expected_action):
            raise ValueError(
                f"Task {self.current_task_id} requires {expected_action.__name__} got {type(action).__name__}"
            )

        # Grader mapping also needs the normalized task name
        grader = GRADER_MAP.get(task_norm) or GRADER_MAP.get(self.current_task_id)
        if grader is None:
            raise ValueError(f"No grader defined for task: {self.current_task_id}")
        
        # Use 'reference' per scenario_bank.json spec
        ground_truth = self._current_scenario["reference"]
        reward = grader(action, ground_truth)

        self.step_count += 1
        self.cumulative_reward += reward.total_score

        next_obs = self._build_observation(step_number=self.step_count)
        return next_obs, reward, True, {}

    def state(self) -> State:
        if (
            self.episode_id is None
            or self.current_task_id is None
            or self.current_scenario_id is None
        ):
            raise RuntimeError("Environment has no active episode. Call reset() first.")

        return State.model_validate(
            {
                "episode_id": self.episode_id,
                "task_id": self.current_task_id,
                "step_count": self.step_count,
                "current_scenario_id": self.current_scenario_id,
                "cumulative_reward": self.cumulative_reward,
            }
        )

    def _build_observation(self, step_number: int) -> Observation:
        if (
            self.episode_id is None
            or self.current_task_id is None
            or self.current_scenario_id is None
            or self._current_scenario is None
        ):
            raise RuntimeError("Environment has no active episode. Call reset() first.")

        # In scenario_bank.json, the scenario data is under "context"
        context = self._current_scenario.get("context", {})
        
        return Observation.model_validate(
            {
                "task_id": self.current_task_id,
                "scenario_id": self.current_scenario_id,
                "context": str(context),  # Convert dict to string for observation
                "available_actions": ["submit"], # Default generic action
                "step_number": step_number,
                "episode_id": self.episode_id,
            }
        )
