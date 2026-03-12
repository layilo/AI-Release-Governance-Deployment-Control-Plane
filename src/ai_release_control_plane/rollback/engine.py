from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.rollout.exposure import ExposureController
from ai_release_control_plane.schemas.models import RollbackDecision


class RollbackEngine:
    def __init__(self, exposure: ExposureController) -> None:
        self.exposure = exposure

    def decide(
        self,
        candidate_id: str,
        should_rollback: bool,
        trigger: str,
        reason: str,
        target_bundle_id: str | None,
    ) -> RollbackDecision:
        return RollbackDecision(
            candidate_id=candidate_id,
            should_rollback=should_rollback,
            trigger=trigger,
            reason=reason,
            target_bundle_id=target_bundle_id,
            created_at=datetime.utcnow(),
        )

    def execute(self, environment: str, bundle_id: str) -> None:
        self.exposure.disable(environment, bundle_id)
