from __future__ import annotations

from pathlib import Path

from ai_release_control_plane.runtime.control_plane import ControlPlane


def test_mock_e2e_canary_rollback(temp_dirs):
    cp = ControlPlane(profile="local-demo", scenario="rollback_canary")
    bundle = cp.register_bundle(Path("configs/bundles/canary_failure.yaml"))
    cand = cp.create_candidate(bundle.bundle_id)
    assert cp.evaluate_offline(cand.candidate_id, "prod").passed
    rollout = cp.start_rollout(cand.candidate_id, "prod", "canary")
    rr = cp.run_rollout_until_decision(rollout["rollout_id"])
    assert rr["status"] == "rolled_back"
    memo = cp.report(cand.candidate_id, "json")
    assert memo["recommendation"] == "rollback"
