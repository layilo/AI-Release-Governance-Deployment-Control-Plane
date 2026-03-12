from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.observability.provider import ObservabilityProvider
from ai_release_control_plane.schemas.models import (
    CanaryAnalysisResult,
    PromotionAction,
    ReleaseEnvironment,
    RolloutStep,
)


class CanaryEngine:
    def __init__(self, observability: ObservabilityProvider) -> None:
        self.observability = observability

    def evaluate_step(
        self,
        candidate_id: str,
        bundle_id: str,
        environment: ReleaseEnvironment,
        step: RolloutStep,
    ) -> tuple[CanaryAnalysisResult, object]:
        online = self.observability.collect_online_gate(
            candidate_id=candidate_id,
            bundle_id=bundle_id,
            environment=environment,
            exposure_percent=step.exposure_percent,
        )
        if online.passed:
            recommendation = PromotionAction.promote
            reasons: list[str] = []
            passed = True
            confidence = 0.92
        else:
            recommendation = PromotionAction.rollback
            reasons = list(online.blocking_reasons)
            passed = False
            confidence = 0.35
        result = CanaryAnalysisResult(
            candidate_id=candidate_id,
            passed=passed,
            step_name=step.name,
            exposure_percent=step.exposure_percent,
            blast_radius_estimate=step.exposure_percent / 100.0,
            confidence=confidence,
            recommendation=recommendation,
            reasons=reasons,
            created_at=datetime.utcnow(),
        )
        return result, online
