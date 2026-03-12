from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.schemas.models import PromotionAction, ShadowTestResult


class ShadowEngine:
    def __init__(self, scenario: str = "success") -> None:
        self.scenario = scenario

    def run(self, candidate_id: str, requests: int = 200) -> ShadowTestResult:
        if self.scenario == "shadow_disagreement":
            disagreement = 0.18
            schema = 0.08
            latency_delta = 120
            cost_delta = 1.35
            passed = False
            rec = PromotionAction.hold
        else:
            disagreement = 0.03
            schema = 0.01
            latency_delta = 12
            cost_delta = 1.05
            passed = True
            rec = PromotionAction.promote
        return ShadowTestResult(
            candidate_id=candidate_id,
            passed=passed,
            requests_tested=requests,
            disagreement_rate=disagreement,
            schema_mismatch_rate=schema,
            latency_delta_ms=latency_delta,
            cost_delta_ratio=cost_delta,
            recommendation=rec,
            details={"mode": "simulated", "scenario": self.scenario},
            created_at=datetime.utcnow(),
        )
