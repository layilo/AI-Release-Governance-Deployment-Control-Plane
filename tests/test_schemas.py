from __future__ import annotations

from datetime import datetime

from ai_release_control_plane.schemas.models import ArtifactRef, ReleaseBundle


def test_release_bundle_schema_validation():
    bundle = ReleaseBundle(
        bundle_id="b1",
        version="v1",
        prompt_refs=[ArtifactRef(artifact_id="p", version="v1")],
        workflow_refs=[],
        serving_config_refs=[],
        safety_policy_refs=[],
        owner_team="team",
        created_at=datetime.utcnow(),
        source_environment="dev",
        target_environment="staging",
    )
    assert bundle.bundle_id == "b1"
    assert bundle.prompt_refs[0].artifact_id == "p"
