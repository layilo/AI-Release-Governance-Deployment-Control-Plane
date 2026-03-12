from __future__ import annotations

from pathlib import Path


SCENARIO_TO_BUNDLE = {
    "success": Path("configs/bundles/full_bundle_success.yaml"),
    "blocked_offline": Path("configs/bundles/offline_blocked.yaml"),
    "rollback_canary": Path("configs/bundles/canary_failure.yaml"),
    "shadow_disagreement": Path("configs/bundles/shadow_disagreement.yaml"),
}


def bundle_for_scenario(scenario: str) -> Path:
    return SCENARIO_TO_BUNDLE.get(scenario, SCENARIO_TO_BUNDLE["success"])
