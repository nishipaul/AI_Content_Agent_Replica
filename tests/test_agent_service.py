"""
Agent service tests: config helpers, build_agent_inputs, generate_response.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agent.api.agent_service import (
    build_agent_inputs,
    generate_response,
    get_agent_runtime_config,
    is_kafka_enabled,
    is_rest_api_enabled,
    is_websocket_enabled,
    run_agentic_crew,
)


@pytest.mark.unit
def test_build_agent_inputs_dict_survey_data() -> None:
    """build_agent_inputs serializes dict survey_data to JSON string (key ends with _data)."""
    inp = build_agent_inputs(
        smtip_tid="tid",
        smtip_feature="feat",
        model="auto-route",
        user_id="u",
        session_id="s",
        tags=["t"],
        locale="en-US",
        survey_data={"survey_id": "s1", "responses": []},
    )
    assert inp["locale"] == "en-US"
    assert inp["smtip_tid"] == "tid"
    assert inp["smtip_feature"] == "feat"
    assert inp["model"] == "auto-route"
    assert inp["user_id"] == "u"
    assert inp["session_id"] == "s"
    assert inp["tags"] == ["t"]
    assert isinstance(inp["survey_data"], str)
    assert "survey_id" in inp["survey_data"]


@pytest.mark.unit
def test_build_agent_inputs_str_survey_data() -> None:
    """build_agent_inputs leaves survey_data as-is when already string."""
    raw = '{"survey_id":"s1"}'
    inp = build_agent_inputs(
        smtip_tid="tid",
        smtip_feature="feat",
        model="auto-route",
        locale="en-US",
        survey_data=raw,
    )
    assert inp["survey_data"] == raw
    assert inp["user_id"] == ""
    assert inp["session_id"] == ""
    assert inp["tags"] == []


@pytest.mark.unit
def test_get_agent_runtime_config_has_endpoints() -> None:
    """get_agent_runtime_config returns dict with endpoints (from master_config)."""
    config = get_agent_runtime_config(reload=True)
    assert "endpoints" in config
    assert "rest_api_enabled" in config["endpoints"]
    assert "kafka_enabled" in config["endpoints"]
    assert "websocket_enabled" in config["endpoints"]


@pytest.mark.unit
def test_is_rest_api_enabled_is_bool() -> None:
    """is_rest_api_enabled returns bool."""
    v = is_rest_api_enabled(reload_config=True)
    assert isinstance(v, bool)


@pytest.mark.unit
def test_is_websocket_enabled_is_bool() -> None:
    """is_websocket_enabled returns bool."""
    v = is_websocket_enabled(reload_config=True)
    assert isinstance(v, bool)


@pytest.mark.unit
def test_is_kafka_enabled_is_bool() -> None:
    """is_kafka_enabled returns bool."""
    v = is_kafka_enabled(reload_config=True)
    assert isinstance(v, bool)


@pytest.mark.unit
def test_run_agentic_crew_returns_mock_when_patched() -> None:
    """run_agentic_crew returns mock result when crew is patched (no real LLM call)."""
    from agent.crew import Insight, SurveySummaryWithComments

    mock_data = SurveySummaryWithComments(
        summary="[MOCK] Survey summary.",
        insights=[Insight(content="[MOCK] Insight.", comment_ids=["c1"])],
        recommendations=["[MOCK] Recommendation."],
    )

    class _MockResult:
        pydantic = mock_data

    async def _mock_crew(_inputs):
        return _MockResult()

    with patch("agent.api.agent_service.BoilerplateCrew") as mock_crew_cls:
        mock_instance = mock_crew_cls.return_value
        mock_instance.run_with_tracing = lambda *a, **k: _MockResult()
        result = asyncio.run(
            run_agentic_crew(
                {
                    "smtip_tid": "t",
                    "smtip_feature": "f",
                    "model": "auto-route",
                    "survey_data": "{}",
                }
            )
        )
    assert hasattr(result, "pydantic")
    assert result.pydantic.summary.startswith("[MOCK]")


@pytest.mark.unit
def test_generate_response_success_when_crew_mocked() -> None:
    """generate_response returns success and data when run_agentic_crew is patched."""
    from tests.conftest import _mock_crew_result

    async def _mock_run(_inputs):
        return _mock_crew_result()

    with patch("agent.api.agent_service.run_agentic_crew", side_effect=_mock_run):
        resp = asyncio.run(
            generate_response(
                smtip_tid="tid",
                smtip_feature="feat",
                model="auto-route",
                locale="en-US",
                survey_data={"survey_id": "s", "responses": []},
            )
        )
    assert resp.success is True
    assert resp.content is not None
    assert resp.content.summary.startswith("[MOCK]")
    assert resp.error is None
    assert resp.latency_seconds is not None


@pytest.mark.unit
def test_generate_response_failure_when_crew_raises() -> None:
    """generate_response returns success=False and error when crew raises."""

    async def _mock_raise(_inputs):
        raise RuntimeError("Crew failed")

    with patch("agent.api.agent_service.run_agentic_crew", side_effect=_mock_raise):
        resp = asyncio.run(
            generate_response(
                smtip_tid="tid",
                smtip_feature="feat",
                model="auto-route",
                locale="en-US",
                survey_data={"survey_id": "s", "responses": []},
            )
        )
    assert resp.success is False
    assert resp.content is None
    assert resp.error == "Crew failed"
    assert resp.latency_seconds is not None
