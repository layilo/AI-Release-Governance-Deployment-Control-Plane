from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


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
