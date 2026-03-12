from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ai_release_control_plane.release.diff import diff_bundles
from ai_release_control_plane.schemas.models import ReleaseBundle, ReleaseEnvironment, ReleaseLineageRecord


def create_lineage_record(
    environment: ReleaseEnvironment,
    previous: ReleaseBundle | None,
    new: ReleaseBundle,
    actor: str,
) -> ReleaseLineageRecord:
    changed: list[str]
    if previous is None:
        changed = ["initial_promotion"]
    else:
        d = diff_bundles(previous, new)
        changed = d["added"] + d["removed"]
    return ReleaseLineageRecord(
        record_id=f"lineage_{uuid4().hex[:10]}",
        environment=environment,
        previous_bundle_id=previous.bundle_id if previous else None,
        new_bundle_id=new.bundle_id,
        changed_artifacts=changed,
        changed_at=datetime.utcnow(),
        changed_by=actor,
    )
