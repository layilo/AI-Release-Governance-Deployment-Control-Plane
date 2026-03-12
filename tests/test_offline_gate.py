from __future__ import annotations

from pathlib import Path

from ai_release_control_plane.runtime.control_plane import ControlPlane


def test_offline_gate_blocked_scenario(temp_dirs):
    cp = ControlPlane(profile="local-demo", scenario="blocked_offline")
    bundle = cp.register_bundle(Path("configs/bundles/offline_blocked.yaml"))
    cand = cp.create_candidate(bundle.bundle_id)
    result = cp.evaluate_offline(cand.candidate_id, "prod")
    assert result.passed is False
    assert result.blocking_reasons
