from __future__ import annotations

from ai_release_control_plane.shadow.engine import ShadowEngine


def test_shadow_disagreement_scenario():
    engine = ShadowEngine(scenario="shadow_disagreement")
    result = engine.run("cand_1", requests=100)
    assert result.passed is False
    assert result.disagreement_rate > 0.1
