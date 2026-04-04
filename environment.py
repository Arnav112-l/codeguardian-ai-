from __future__ import annotations

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
from scenario_bank import SCENARIO_BANK


class CodingEnvironment:
    def __init__(self, scenario_bank: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.scenario_bank = scenario_bank or SCENARIO_BANK
        self.episode_id: str | None = None
        self.current_task_id: str | None = None
        self.current_scenario_id: str | None = None
        self._current_scenario: dict[str, Any] | None = None
        self.step_count: int = 0
        self.cumulative_reward: float = 0.0

    def reset(self, task_id: str, scenario_index: int) -> Observation:
        if task_id not in self.scenario_bank:
            raise ValueError(f"Unknown task_id: {task_id}")

        scenarios = self.scenario_bank[task_id]
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

        expected_action = {
            "task_triage": TriageAction,
            "task_security_audit": SecurityAuditAction,
            "task_dependency_update": DependencyAction,
            "task_dependency": DependencyAction,
        }.get(self.current_task_id)

        if expected_action is None:
            raise ValueError(f"No action contract defined for task: {self.current_task_id}")

        if not isinstance(action, expected_action):
            raise ValueError(
                f"Task {self.current_task_id} requires {expected_action.__name__} got {type(action).__name__}"
            )

        grader = GRADER_MAP.get(self.current_task_id)
        if grader is None:
            raise ValueError(f"No grader defined for task: {self.current_task_id}")
        
        ground_truth = self._current_scenario["ground_truth"]
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

        return Observation.model_validate(
            {
                "task_id": self.current_task_id,
                "scenario_id": self.current_scenario_id,
                "context": self._current_scenario["context"],
                "available_actions": self._current_scenario["available_actions"],
                "step_number": step_number,
                "episode_id": self.episode_id,
            }
        )
