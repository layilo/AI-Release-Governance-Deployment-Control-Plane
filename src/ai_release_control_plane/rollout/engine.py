from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ai_release_control_plane.rollout.exposure import ExposureController
from ai_release_control_plane.schemas.models import RolloutPlan, RolloutStatus
from ai_release_control_plane.storage.repository import ModelRepository


class RolloutEngine:
    def __init__(self, exposure: ExposureController, repo: ModelRepository) -> None:
        self.exposure = exposure
        self.repo = repo

    def start(self, candidate_id: str, bundle_id: str, environment: str, plan: RolloutPlan) -> dict:
        rollout_id = f"rollout_{uuid4().hex[:10]}"
        state = {
            "rollout_id": rollout_id,
            "candidate_id": candidate_id,
            "bundle_id": bundle_id,
            "environment": environment,
            "plan_id": plan.plan_id,
            "strategy": plan.strategy,
            "status": RolloutStatus.running.value,
            "current_step": 0,
            "steps": [s.model_dump(mode="json") for s in plan.steps],
            "history": [],
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.repo.storage.put("rollouts", rollout_id, state)
        return state

    def get(self, rollout_id: str) -> dict | None:
        return self.repo.storage.get("rollouts", rollout_id)

    def _save(self, rollout: dict) -> dict:
        rollout["updated_at"] = datetime.utcnow().isoformat()
        self.repo.storage.put("rollouts", rollout["rollout_id"], rollout)
        return rollout

    def pause(self, rollout_id: str) -> dict:
        rollout = self._require_rollout(rollout_id)
        rollout["status"] = RolloutStatus.paused.value
        return self._save(rollout)

    def resume(self, rollout_id: str) -> dict:
        rollout = self._require_rollout(rollout_id)
        rollout["status"] = RolloutStatus.running.value
        return self._save(rollout)

    def abort(self, rollout_id: str, reason: str) -> dict:
        rollout = self._require_rollout(rollout_id)
        self.exposure.disable(rollout["environment"], rollout["bundle_id"])
        rollout["status"] = RolloutStatus.aborted.value
        rollout["history"].append(
            {"event": "abort", "reason": reason, "at": datetime.utcnow().isoformat()}
        )
        return self._save(rollout)

    def apply_next_step(self, rollout_id: str) -> dict:
        rollout = self._require_rollout(rollout_id)
        if rollout["status"] != RolloutStatus.running.value:
            return rollout
        idx = rollout["current_step"]
        if idx >= len(rollout["steps"]):
            rollout["status"] = RolloutStatus.completed.value
            return self._save(rollout)
        step = rollout["steps"][idx]
        exposure = int(step.get("exposure_percent", 0))
        self.exposure.set_exposure(rollout["environment"], rollout["bundle_id"], exposure)
        rollout["history"].append(
            {"event": "step_applied", "step": step["name"], "exposure": exposure, "at": datetime.utcnow().isoformat()}
        )
        rollout["current_step"] += 1
        if rollout["current_step"] >= len(rollout["steps"]):
            rollout["status"] = RolloutStatus.completed.value
        return self._save(rollout)

    def _require_rollout(self, rollout_id: str) -> dict:
        rollout = self.get(rollout_id)
        if rollout is None:
            msg = f"Rollout not found: {rollout_id}"
            raise KeyError(msg)
        return rollout
