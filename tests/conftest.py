from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def temp_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state = tmp_path / "state"
    reports = tmp_path / "reports"
    monkeypatch.setenv("ARCP_STATE_DIR", str(state))
    monkeypatch.setenv("ARCP_REPORTS_DIR", str(reports))
    return {"state": state, "reports": reports}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch):
    for k in ["ARCP_PROFILE", "ARCP_MODE"]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    yield
