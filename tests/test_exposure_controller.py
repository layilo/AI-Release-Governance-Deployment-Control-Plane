from __future__ import annotations

from ai_release_control_plane.rollout.exposure import MockExposureController


def test_exposure_assignment_is_sticky():
    ctrl = MockExposureController()
    a = ctrl.assign("user-123", 10)
    b = ctrl.assign("user-123", 10)
    assert a == b
