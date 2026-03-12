from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ai_release_control_plane.schemas.models import OfflineGateResult


class EvaluationProvider(ABC):
    @abstractmethod
    def run_offline(self, candidate_id: str, bundle_id: str) -> OfflineGateResult:
        raise NotImplementedError


class MockEvaluationProvider(EvaluationProvider):
    def __init__(self, scenario: str = "success") -> None:
        self.scenario = scenario

    def run_offline(self, candidate_id: str, bundle_id: str) -> OfflineGateResult:
        if self.scenario == "blocked_offline":
            return OfflineGateResult(
                candidate_id=candidate_id,
                passed=False,
                quality_score=0.71,
                regression_delta=-0.18,
                structured_output_validity=0.86,
                latency_ms=1300,
                token_usage=980,
                cost_per_1k=0.045,
                safety_score=0.8,
                composite_score=0.68,
                blocking_reasons=["quality_score_below_threshold", "regression_exceeds_tolerance"],
                warnings=[],
                created_at=datetime.utcnow(),
            )
        return OfflineGateResult(
            candidate_id=candidate_id,
            passed=True,
            quality_score=0.91,
            regression_delta=-0.01,
            structured_output_validity=0.98,
            latency_ms=720,
            token_usage=700,
            cost_per_1k=0.024,
            safety_score=0.96,
            composite_score=0.92,
            blocking_reasons=[],
            warnings=[],
            created_at=datetime.utcnow(),
        )
