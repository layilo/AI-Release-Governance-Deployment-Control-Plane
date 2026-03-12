from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.release.diff import diff_bundles
from ai_release_control_plane.schemas.models import ArtifactRef, ReleaseBundle


def _bundle(bundle_id: str, prompt_version: str) -> ReleaseBundle:
    return ReleaseBundle(
        bundle_id=bundle_id,
        version="v1",
        prompt_refs=[ArtifactRef(artifact_id="prompt", version=prompt_version)],
        workflow_refs=[ArtifactRef(artifact_id="wf", version="v1")],
        serving_config_refs=[],
        safety_policy_refs=[],
        owner_team="ai",
        created_at=datetime.utcnow(),
        source_environment="staging",
        target_environment="prod",
    )


def test_diff_bundles_added_removed():
    d = diff_bundles(_bundle("a", "v1"), _bundle("b", "v2"))
    assert "prompt:prompt:v2" in d["added"]
    assert "prompt:prompt:v1" in d["removed"]
