from __future__ import annotations

import os
import subprocess
import sys


def test_cli_doctor_command(temp_dirs):
    env = os.environ.copy()
    env["ARCP_STATE_DIR"] = str(temp_dirs["state"])
    env["ARCP_REPORTS_DIR"] = str(temp_dirs["reports"])
    proc = subprocess.run(
        [sys.executable, "-m", "ai_release_control_plane.cli", "doctor", "--profile", "local-demo"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert '"ok"' in proc.stdout
