from __future__ import annotations

from ai_release_control_plane.canary.engine import CanaryEngine
from ai_release_control_plane.observability.provider import MockObservabilityProvider
from ai_release_control_plane.schemas.models import RolloutStep


def test_canary_failure_detected():
    engine = CanaryEngine(MockObservabilityProvider(scenario="rollback_canary"))
    step = RolloutStep(name="canary-10", step_type="canary", exposure_percent=10)
    canary, online = engine.evaluate_step("cand_1", "bundle_1", "prod", step)
    assert not canary.passed
    assert not online.passed
