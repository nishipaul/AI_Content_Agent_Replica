#!/usr/bin/env python3
"""Test WebSocket /ws/survey-summary endpoint.

Reads SMTIP_TID, SMTIP_FEATURE, and AGENT_NAME from the repo's .env file
(via python-dotenv) so all scripts share the same tenant/service values.

Runs against all combinations of API mode (completions, responses) and
reasoning_effort (None, low).  Override the model used for the responses API
via LLM_RESPONSES_MODEL env var (default: same as LLM_COMPLETIONS_MODEL).
"""

import asyncio
import json
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

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets", file=sys.stderr)
    sys.exit(2)

BASE_URL = (
    os.getenv("BASE_URL", "http://0.0.0.0:8000")
    .rstrip("/")
    .replace("http://", "ws://")
    .replace("https://", "wss://")
)
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
            "text": "Sample feedback for WebSocket test.",
            "department": "Engineering",
            "location": "Mumbai, Maharashtra, India",
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
        "user_id": "scripts-ws-test",
        "session_id": f"scripts-ws-{api}-{reasoning_effort or 'none'}",
        "tags": [f"scripts-ws-{api}", f"reasoning-{reasoning_effort or 'none'}"],
    }
    if reasoning_effort is not None:
        payload["reasoning_effort"] = reasoning_effort
    return payload


def _label(api: str, reasoning_effort: str | None) -> str:
    return f"api={api} reasoning_effort={reasoning_effort or 'None'}"


async def _run_one(api: str, reasoning_effort: str | None) -> str | None:
    """Run a single WS test case. Returns None on success, error string on failure."""
    label = _label(api, reasoning_effort)
    uri = f"{BASE_URL}{ROUTER_PREFIX}/ws/survey-summary"
    payload = _build_payload(api, reasoning_effort)

    try:
        async with websockets.connect(uri, open_timeout=10, close_timeout=5) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            if data.get("type") != "connected":
                return f"[{label}] expected type=connected, got {data}"

            await ws.send(json.dumps(payload))

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=120)
                data = json.loads(msg)
                if data.get("type") == "progress":
                    continue
                if data.get("type") == "result":
                    p = data.get("payload", {})
                    print(
                        "OK  WS /ws/survey-summary [%s]: success=%s latency_seconds=%s"
                        % (label, p.get("success"), p.get("latency_seconds"))
                    )
                    return None
                if data.get("type") == "error":
                    return f"[{label}] {data.get('message', data)}"
                return f"[{label}] unexpected message: {data}"
    except Exception as e:
        skip_env = os.getenv("SKIP_DISABLED_ENDPOINTS", "").strip().lower()
        if skip_env in ("1", "true", "yes"):
            if getattr(e, "status_code", None) == 404 or "404" in str(e):
                print(f"SKIP WS /ws/survey-summary [{label}] (endpoint disabled)")
                return None
        return f"[{label}] {e}"


async def run_all() -> int:
    if not SMTIP_TID or not SMTIP_FEATURE:
        print(
            "FAIL: SMTIP_TID and SMTIP_FEATURE must be set (via .env or environment).",
            file=sys.stderr,
        )
        return 1

    failed: list[str] = []
    for tc in TEST_CASES:
        api = tc["api"] or ""
        effort = tc["reasoning_effort"]
        err = await _run_one(api, effort)
        if err:
            print(f"FAIL WS /ws/survey-summary: {err}", file=sys.stderr)
            failed.append(_label(api, effort))

    if failed:
        print(
            "\n%d/%d WS test case(s) failed: %s"
            % (len(failed), len(TEST_CASES), ", ".join(failed)),
            file=sys.stderr,
        )
        return 1

    print("\nAll %d WS test cases passed." % len(TEST_CASES))
    return 0


def main() -> int:
    return asyncio.run(run_all())


if __name__ == "__main__":
    sys.exit(main())
