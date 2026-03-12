from __future__ import annotations

from pathlib import Path

from ai_release_control_plane.runtime.control_plane import ControlPlane


def test_mock_e2e_success(temp_dirs):
    cp = ControlPlane(profile="local-demo", scenario="success")
    bundle = cp.register_bundle(Path("configs/bundles/full_bundle_success.yaml"))
    cand = cp.create_candidate(bundle.bundle_id)
    offline = cp.evaluate_offline(cand.candidate_id, "prod")
    assert offline.passed
    shadow = cp.run_shadow(cand.candidate_id)
    assert shadow.passed
    rollout = cp.start_rollout(cand.candidate_id, "prod", "canary")
    rr = cp.run_rollout_until_decision(rollout["rollout_id"])
    assert rr["status"] in {"completed", "running"}
    cp.approve(cand.candidate_id, "release-manager", "release_board", "ok")
    decision = cp.promote(cand.candidate_id, actor="release-manager")
    assert decision.approved
    memo = cp.report(cand.candidate_id, "json")
    assert memo["recommendation"] == "promote"
