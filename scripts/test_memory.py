#!/usr/bin/env python
"""
Integration test: survey summary crew with Redis-backed CrewAI external memory.

Uses BoilerplateCrew with use_crewai_external_memory=True and the same
Redis/CrewAIStorageFactory as the SDK. Verifies:

  1. Memory is written to Redis after each run (storage.search returns entries).
  2. Stored entries contain content from the runs (keywords from survey data or outputs).

Uses a dedicated user_id so real user memory is not affected. Run from project root:

  uv run python scripts/test_memory.py

If Azure Prompt Shield (or similar) blocks the LLM call, the trigger is often the task
prompt wording (e.g. "Strictly follow", "NEVER", "DO NOT") in config/tasks.yaml. This
script uses softened wording there. To skip crew runs and only verify Redis + storage
wiring, set SKIP_LLM_MEMORY_TEST=1.

Exit code 0 = all checks passed, 1 = failure (with message).
"""

from __future__ import annotations

import os
import sys

# Project root and .env (script lives in scripts/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_script_dir, os.pardir))
_env_file = os.path.join(_repo_root, ".env")
if os.path.isfile(_env_file):
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass

# Paths for imports (agent lives under src/)
_src = os.path.join(_repo_root, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Test config: distinct user so we don't touch real user memory
TEST_USER_ID = "test-memory-script"
TEST_SESSION_ID = "test-memory-session"
AGENT_NAME = os.environ.get("AGENT_NAME", "survey-summary")
# Keywords we inject in survey responses and then assert in storage.
# Use neutral, realistic survey wording only. Avoid "test", "TEST_", or any token that
# can trigger Azure Prompt Shield / content guardrails (attack detection).
MSG1 = "We have good alignment on the Q3 timeline and budget allocation."
MSG2 = "Colleagues would like more clarity on priorities and capacity planning."
KEYWORDS_STORED = ("timeline", "Q3", "budget", "clarity", "priorities", "Engineering")


def _minimal_survey(response_text: str, comment_id: str = "mem-1") -> dict:
    """Minimal survey payload with one response for the analysis task. Neutral ids to avoid guardrails."""
    return {
        "survey_id": "memory-check-survey",
        "survey_name": "Employee feedback survey",
        "responses": [
            {
                "comment_id": comment_id,
                "text": response_text,
                "department": "Engineering",
                "location": "Remote",
            }
        ],
    }


def _result_text(result: object) -> str:
    if hasattr(result, "raw"):
        return str(result.raw)
    if hasattr(result, "pydantic"):
        return str(result.pydantic)
    if isinstance(result, str):
        return result
    return str(result)


def main() -> int:
    from agent.api.agent_service import build_agent_inputs
    from agent.api.constants import SERVICE_ID, SERVICE_NAME
    from agent.crew import BoilerplateCrew

    try:
        from ai_infra_python_sdk_core.ai_infra.connections import (
            CrewAIStorageFactory,
            RedisConnection,
        )
    except ImportError as e:
        print(
            "FAIL: Could not import RedisConnection/CrewAIStorageFactory. "
            "Ensure ai-infra-python-sdk-core is installed (uv sync)."
        )
        print("Error:", e)
        return 1

    tenant = os.environ.get("SMTIP_TID", "")
    feature = os.environ.get("SMTIP_FEATURE", "") or os.environ.get("SMTIP_SERVICE", "")
    if not tenant or not feature:
        print(
            "FAIL: SMTIP_TID and SMTIP_FEATURE must be set (via .env or environment).",
            file=sys.stderr,
        )
        return 1
    model = os.environ.get("MODEL", "auto-route")

    redis_conn = RedisConnection.initialize_from_env()
    crewai_factory = CrewAIStorageFactory.initialize_from_env()

    crew = BoilerplateCrew(
        smtip_tid=tenant,
        smtip_feature=feature,
        model=model or "auto-route",
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        service_id=SERVICE_ID,
        service_name=SERVICE_NAME,
        agent_id=SERVICE_ID,
        trace_name="test-memory-crew",
        enable_observability=False,
        use_crewai_external_memory=True,
    )
    storage = crewai_factory.create_storage(
        smtip_tid=tenant,
        smtip_feature=feature,
        user_id=TEST_USER_ID,
        agent_id=SERVICE_ID,
    )

    if not redis_conn.connector.is_available():
        print(
            "FAIL: Redis is not available. Set redis_* / REDIS_* in .env (or vault) to a reachable Redis."
        )
        redis_conn.close()
        crewai_factory.close()
        return 1

    # Start clean for this test user
    storage.reset()

    skip_llm = os.environ.get("SKIP_LLM_MEMORY_TEST", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if skip_llm:
        # Verify storage write/read without calling the crew (avoids guardrail when LLM is protected).
        print(
            "SKIP_LLM_MEMORY_TEST=1: skipping crew runs; verifying Redis storage only..."
        )
        try:
            storage.save(MSG1, metadata={"source": "test_memory_script"})
        except Exception as e:
            print(f"FAIL: storage.save failed: {e}")
            redis_conn.close()
            crewai_factory.close()
            return 1
        entries = storage.search("", limit=10)
        if len(entries) < 1:
            print("FAIL: After storage.save, expected at least 1 entry, got 0.")
            redis_conn.close()
            crewai_factory.close()
            return 1
        combined = " ".join(str(e.get("value", "")) for e in entries).lower()
        if not any(k.lower() in combined for k in KEYWORDS_STORED):
            print(
                f"FAIL: Stored content does not contain expected keywords. Entries: {entries[:2]}..."
            )
            redis_conn.close()
            crewai_factory.close()
            return 1
        storage.reset()
        redis_conn.close()
        crewai_factory.close()
        print("Storage-only check passed (Redis write/read verified).")
        return 0

    # ---- Run 1: first survey (MSG1) ----
    print("Run 1: sending survey with first message...")
    inputs1 = build_agent_inputs(
        smtip_tid=tenant,
        smtip_feature=feature,
        model=model,
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        tags=["test", "memory"],
        locale="en-US",
        survey_data=_minimal_survey(MSG1),
    )
    try:
        result1 = crew.run_with_tracing(inputs=inputs1, tags=["test", "memory"])
    except Exception as e:
        print(f"FAIL: Run 1 crew.run_with_tracing failed: {e}")
        redis_conn.close()
        crewai_factory.close()
        return 1
    _ = _result_text(result1)

    entries = storage.search("", limit=10)
    if len(entries) < 1:
        print(
            f"FAIL: After run 1, expected at least 1 memory entry, got {len(entries)}."
        )
        redis_conn.close()
        crewai_factory.close()
        return 1
    combined = " ".join(str(e.get("value", "")) for e in entries).lower()
    if not any(k.lower() in combined for k in KEYWORDS_STORED):
        print(
            f"FAIL: Run 1 memory entries do not contain expected keywords. Entries (first 2): {entries[:2]}..."
        )
        redis_conn.close()
        crewai_factory.close()
        return 1
    print("  -> memory entries after run 1:", len(entries))

    # ---- Run 2: second survey (MSG2) ----
    print("Run 2: sending survey with second message...")
    inputs2 = build_agent_inputs(
        smtip_tid=tenant,
        smtip_feature=feature,
        model=model,
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        tags=["test", "memory"],
        locale="en-US",
        survey_data=_minimal_survey(MSG2, comment_id="mem-2"),
    )
    try:
        result2 = crew.run_with_tracing(inputs=inputs2, tags=["test", "memory"])
    except Exception as e:
        print(f"FAIL: Run 2 crew.run_with_tracing failed: {e}")
        redis_conn.close()
        crewai_factory.close()
        return 1
    _result_text(result2)

    entries = storage.search("", limit=10)
    if len(entries) < 2:
        print(
            f"FAIL: After run 2, expected at least 2 memory entries, got {len(entries)}."
        )
        redis_conn.close()
        crewai_factory.close()
        return 1
    print("  -> memory entries after run 2:", len(entries))

    combined = " ".join(str(e.get("value", "")) for e in entries).lower()
    found = [k for k in KEYWORDS_STORED if k.lower() in combined]
    if not found:
        print(
            f"FAIL: Run 2 memory entries do not contain any of {KEYWORDS_STORED}. Entries (first 2): {entries[:2]}..."
        )
        redis_conn.close()
        crewai_factory.close()
        return 1
    print(f"  -> stored content contains keywords: {found}")

    # Clean up test data
    storage.reset()
    redis_conn.close()
    crewai_factory.close()
    print("All memory checks passed (written and retrieved).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
