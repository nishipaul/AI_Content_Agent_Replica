#!/usr/bin/env python3
"""Test POST /survey-summary (REST survey summary endpoint).

Reads SMTIP_TID, SMTIP_FEATURE, and AGENT_NAME from the repo's .env file
(via python-dotenv) so all scripts share the same tenant/service values.

Runs against all combinations of API mode (completions, responses) and
reasoning_effort (None, low).  Override the model used for the responses API
via LLM_RESPONSES_MODEL env var (default: same as LLM_COMPLETIONS_MODEL).
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"
if _ENV_FILE.is_file():
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE)
    except ImportError:
        pass

import requests

BASE_URL = os.getenv("BASE_URL", "http://0.0.0.0:8000").rstrip("/")
ROUTER_PREFIX = "/v1/ai-content-agent"
SMTIP_TID = os.getenv("SMTIP_TID", "")
SMTIP_FEATURE = os.getenv("SMTIP_FEATURE", "")
AGENT_NAME = os.getenv("AGENT_NAME", "survey-summary")
LLM_COMPLETIONS_MODEL = os.getenv("LLM_COMPLETIONS_MODEL", "auto-route")
LLM_RESPONSES_MODEL = os.getenv("LLM_RESPONSES_MODEL", LLM_COMPLETIONS_MODEL)

SAMPLE_SURVEY_DATA = {
    "survey_id": "e137e4b4-3399-476b-ad91-0f297f2de001",
    "survey_name": "JP | Manager survey (2) > Mixed responses",
    "responses": [
        {
            "comment_id": "23c88c5a-654b-4f68-9d6a-5a51e1df7d94",
            "text": "These talks rarely happen, so I sense a bit left in the dark about my progression path.",
            "department": "Engineering",
            "location": "Mumbai, Maharashtra, India",
        },
        {
            "comment_id": "ba0bb53a-314d-4e7d-a498-2570a2e01325",
            "text": "Could have used clearer task assignments and better time estimates.",
            "department": "Finance",
            "location": "Bangalore, Karnataka, India",
        },
    ],
}

TEST_CASES: list[dict[str, str | None]] = [
    {"api": "completions", "reasoning_effort": None},
    {"api": "completions", "reasoning_effort": "low"},
    {"api": "responses", "reasoning_effort": None},
    {"api": "responses", "reasoning_effort": "low"},
]


def _build_payload(api: str, reasoning_effort: str | None) -> dict:
    model = LLM_RESPONSES_MODEL if api == "responses" else LLM_COMPLETIONS_MODEL
    payload: dict = {
        "locale": "en-US",
        "survey_data": SAMPLE_SURVEY_DATA,
        "smtip_tid": SMTIP_TID,
        "smtip_feature": SMTIP_FEATURE,
        "model": model,
        "user_id": "scripts-test",
        "session_id": f"scripts-rest-{api}-{reasoning_effort or 'none'}",
        "tags": [f"scripts-test-{api}", f"reasoning-{reasoning_effort or 'none'}"],
    }
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    return payload


def _label(api: str, reasoning_effort: str | None) -> str:
    return f"api={api} reasoning_effort={reasoning_effort or 'None'}"


def main() -> int:
    if not SMTIP_TID or not SMTIP_FEATURE:
        print(
            "FAIL: SMTIP_TID and SMTIP_FEATURE must be set (via .env or environment).",
            file=sys.stderr,
        )
        return 1

    url = f"{BASE_URL}{ROUTER_PREFIX}/survey-summary"
    failed: list[str] = []

    for tc in TEST_CASES:
        api = tc["api"] or ""
        effort = tc["reasoning_effort"]
        label = _label(api, effort)
        payload = _build_payload(api, effort)

        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            assert data.get("success") is True, f"success={data.get('success')}"
            print(
                "OK  POST /survey-summary [%s]: latency_seconds=%s"
                % (label, data.get("latency_seconds"))
            )
        except requests.exceptions.RequestException as e:
            print(f"FAIL POST /survey-summary [{label}]: {e}", file=sys.stderr)
            if hasattr(e, "response") and e.response is not None:
                print(e.response.text, file=sys.stderr)
            failed.append(label)
        except AssertionError as e:
            print(
                f"FAIL POST /survey-summary [{label}]: {e}",
                file=sys.stderr,
            )
            failed.append(label)

    if failed:
        print(
            "\n%d/%d test case(s) failed: %s"
            % (len(failed), len(TEST_CASES), ", ".join(failed)),
            file=sys.stderr,
        )
        return 1

    print("\nAll %d REST test cases passed." % len(TEST_CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
