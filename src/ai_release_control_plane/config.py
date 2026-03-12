from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        msg = f"Expected mapping at {path}"
        raise ValueError(msg)
    return data


def profile_paths(profile: str) -> dict[str, Path]:
    root = Path.cwd()
    return {
        "environment": root / "configs" / "environments" / f"{profile}.yaml",
        "policy": root / "configs" / "policies" / f"{profile}.yaml",
        "approval": root / "configs" / "approvals" / f"{profile}.yaml",
        "observability": root / "configs" / "observability" / f"{profile}.yaml",
        "rollout": root / "configs" / "rollout_strategies" / f"{profile}.yaml",
    }


def state_dir() -> Path:
    return Path(os.getenv("ARCP_STATE_DIR", "state"))


def reports_dir() -> Path:
    return Path(os.getenv("ARCP_REPORTS_DIR", "reports"))
