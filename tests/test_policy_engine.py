from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.policy.engine import RulePolicyEngine
from ai_release_control_plane.schemas.models import OfflineGateResult, ReleasePolicy


def test_policy_offline_evaluation_passes():
    engine = RulePolicyEngine()
    policy = ReleasePolicy(
        policy_id="p1",
        name="test",
        environment="prod",
        hard_fail_rules={"min_quality_score": 0.8, "max_latency_ms": 1200},
    )
    result = OfflineGateResult(
        candidate_id="c1",
        passed=True,
        quality_score=0.9,
        regression_delta=-0.01,
        structured_output_validity=0.98,
        latency_ms=700,
        token_usage=700,
        cost_per_1k=0.02,
        safety_score=0.95,
        composite_score=0.93,
        created_at=datetime.utcnow(),
    )
    ok, failures, _ = engine.evaluate_offline(policy, result)
    assert ok
    assert failures == []
