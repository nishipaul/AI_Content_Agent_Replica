#!/usr/bin/env python3
"""Run all endpoint tests (survey-summary REST, survey-summary WebSocket). Excludes health and probe APIs.

Loads .env from the repo root so SMTIP_TID, SMTIP_FEATURE, AGENT_NAME (and
other vars) are available to all child test scripts.

When running locally, all tests are run and must pass (WebSocket must be enabled in master_config).
Set SKIP_DISABLED_ENDPOINTS=1 to skip tests for disabled endpoints (e.g. in CI).
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = SCRIPT_DIR.parent
_ENV_FILE = _REPO_ROOT / ".env"
if _ENV_FILE.is_file():
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE)
    except ImportError:
        pass
TESTS = [
    (
        "POST /survey-summary",
        [sys.executable, str(SCRIPT_DIR / "test_survey_summary_rest.py")],
    ),
    (
        "WS /ws/survey-summary",
        [sys.executable, str(SCRIPT_DIR / "test_survey_summary_ws.py")],
    ),
]


def main() -> int:
    # Ensure all tests run (no skip on disabled endpoints) when running the full suite locally
    env = os.environ.copy()
    if "SKIP_DISABLED_ENDPOINTS" not in env:
        env["SKIP_DISABLED_ENDPOINTS"] = "0"
    failed = []
    for name, cmd in TESTS:
        print("Running %s..." % name, flush=True)
        r = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
        if r.returncode != 0:
            failed.append(name)
        print(flush=True)
    if failed:
        print("Failed: %s" % ", ".join(failed), file=sys.stderr)
        return 1
    print("All endpoint tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
