from __future__ import annotations

from ai_release_control_plane.approvals.engine import ApprovalEngine


def test_approval_roles_and_auto():
    engine = ApprovalEngine({"required_by_risk": {"high": ["release_board"]}, "additional_prod_roles": ["sre"]})
    roles = engine.required_roles("high", "prod")
    assert "release_board" in roles
    assert "sre" in roles
    assert engine.auto_approved("low", "staging", "manual")
