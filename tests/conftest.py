"""
Pytest fixtures and configuration for agent API and service tests.

- trace_ai_config is patched at session start so survey-summary route doesn't require real AI Config.
- tenant_exists is patched to True so endpoints don't require real agent-config/Redis.
- run_agentic_crew is patched to return mock result so no real LLM is called.
"""

from __future__ import annotations

from functools import wraps
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_mock_trace_ai_config():
    """No-op decorator that injects _pipeline_ctx so route runs without real AI Config fetch."""

    def _decorator(f):
        @wraps(f)
        async def _wrapper(request, *args, **kwargs):
            if hasattr(request, "session_id"):
                ctx = type(
                    "_PipelineCtx",
                    (),
                    {
                        "session_id": getattr(request, "session_id", None)
                        or "test-session",
                        "trace_id": "test-trace-id",
                        "trace_name": "ai-content-agent",
                        "correlation_id": getattr(request, "correlation_id", None)
                        or "test-correlation-id",
                        "all_tags": getattr(request, "tags", None) or [],
                        "metadata": {},
                    },
                )()
                request._pipeline_ctx = ctx
            return await f(request, *args, **kwargs)

        return _wrapper

    return _decorator


def _make_mock_trace_ws_lifecycle(*outer_args, **outer_kwargs):
    """No-op decorator for WebSocket tracing - just passes through with any args."""

    def _decorator(f):
        @wraps(f)
        async def _wrapper(*args, **kwargs):
            return await f(*args, **kwargs)

        return _wrapper

    return _decorator


# Patch pipeline before any test or agent.api import so survey-summary route never calls real AI Config
_trace_ai_config_patch = patch(
    "ai_infra_python_sdk_core.ai_infra.observability.pipeline.trace_ai_config",
    side_effect=_make_mock_trace_ai_config,
)
_trace_ai_config_patch.start()

# Patch WebSocket lifecycle tracing to avoid decorator issues in tests
_trace_ws_lifecycle_patch = patch(
    "ai_infra_python_sdk_core.ai_infra.observability.pipeline.trace_ws_lifecycle",
    new=_make_mock_trace_ws_lifecycle,
)
_trace_ws_lifecycle_patch.start()


def _mock_crew_result():
    """Result object with .pydantic for tests that hit survey-summary without calling LLM."""
    from agent.crew import Insight, SurveySummaryWithComments

    data = SurveySummaryWithComments(
        summary="[MOCK] Survey summary for testing.",
        insights=[
            Insight(content="[MOCK] Sample insight.", comment_ids=["mock-comment-1"]),
        ],
        recommendations=["[MOCK] Sample recommendation."],
    )

    class _MockResult:
        pydantic = data

    return _MockResult()


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient. Patches tenant_exists and run_agentic_crew so no real agent-config or LLM needed."""
    from agent.api import app

    async def _mock_run_agentic_crew(_inputs):
        return _mock_crew_result()

    with (
        patch(
            "agent.api.routes.tenant_exists",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "agent.api.agent_service.run_agentic_crew",
            side_effect=_mock_run_agentic_crew,
        ),
    ):
        yield TestClient(app)


@pytest.fixture
def sample_survey_payload() -> dict:
    """Minimal valid survey-summary request body."""
    return {
        "locale": "en-US",
        "survey_data": {
            "survey_id": "test-id",
            "survey_name": "Test Survey",
            "responses": [
                {
                    "comment_id": "c1",
                    "text": "Sample comment.",
                    "department": "Engineering",
                    "location": "Remote",
                },
            ],
        },
        "smtip_tid": "test-tenant-id",
        "smtip_feature": "smart_answers",
        "model": "auto-route",
        "user_id": "test-user",
        "session_id": "test-session",
        "tags": ["test"],
    }
