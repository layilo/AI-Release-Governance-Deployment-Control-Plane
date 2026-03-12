from __future__ import annotations

from ai_release_control_plane.schemas.models import ReleaseBundle


def _refs(bundle: ReleaseBundle) -> set[str]:
    rows: set[str] = set()
    for p in bundle.prompt_refs:
        rows.add(f"prompt:{p.artifact_id}:{p.version}")
    for w in bundle.workflow_refs:
        rows.add(f"workflow:{w.artifact_id}:{w.version}")
    for s in bundle.serving_config_refs:
        rows.add(f"serving:{s.artifact_id}:{s.version}")
    for x in bundle.safety_policy_refs:
        rows.add(f"safety:{x.artifact_id}:{x.version}")
    return rows


def diff_bundles(base: ReleaseBundle, candidate: ReleaseBundle) -> dict[str, list[str]]:
    base_refs = _refs(base)
    cand_refs = _refs(candidate)
    return {
        "added": sorted(cand_refs - base_refs),
        "removed": sorted(base_refs - cand_refs),
        "unchanged": sorted(base_refs & cand_refs),
    }
