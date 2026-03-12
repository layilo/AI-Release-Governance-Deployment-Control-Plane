from __future__ import annotations

from ai_release_control_plane.rollback.engine import RollbackEngine
from ai_release_control_plane.rollout.exposure import MockExposureController


def test_rollback_decision_and_execute():
    exposure = MockExposureController()
    engine = RollbackEngine(exposure)
    exposure.set_exposure("prod", "bundle1", 25)
    decision = engine.decide("cand1", True, "canary_failure", "latency spike", "bundle0")
    engine.execute("prod", "bundle1")
    assert decision.should_rollback
    assert exposure.state[("prod", "bundle1")] == 0
