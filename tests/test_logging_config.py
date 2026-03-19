"""
Logging config tests: _resolve_log_level, configure_logging (no crash), get_logger.
Uses env patches; no external services.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from agent.utils.logging_config import (
    DEFAULT_LOG_LEVEL,
    VALID_LOG_LEVELS,
    _resolve_log_level,
    configure_logging,
    event_span,
    get_logger,
    get_logger_without_crew_context,
)
from agent.utils.logging_config.crew_run import CrewRunStartEvent
from agent.utils.logging_config.database import DatabaseStartEvent
from agent.utils.logging_config.events import _mandatory_from_start, make_end_payload
from agent.utils.logging_config.memory import (
    MemoryLoadStartEvent,
    MemorySaveStartEvent,
    MemorySearchStartEvent,
)


@pytest.mark.unit
def test_resolve_log_level_explicit() -> None:
    """_resolve_log_level returns explicit level when valid."""
    assert _resolve_log_level("DEBUG") == "DEBUG"
    assert _resolve_log_level("INFO") == "INFO"
    assert _resolve_log_level("WARNING") == "WARNING"
    assert _resolve_log_level("ERROR") == "ERROR"


@pytest.mark.unit
def test_resolve_log_level_strips_whitespace() -> None:
    """_resolve_log_level strips and accepts '  info  '."""
    assert _resolve_log_level("  info  ") == "INFO"


@pytest.mark.unit
def test_resolve_log_level_invalid_falls_back_to_env_or_default() -> None:
    """_resolve_log_level with invalid explicit level uses env then default."""
    with patch.dict(
        os.environ, {"AI_INFRA_LOG_LEVEL": "", "LOG_LEVEL": ""}, clear=False
    ):
        assert _resolve_log_level("INVALID") == DEFAULT_LOG_LEVEL
    with patch.dict(
        os.environ, {"AI_INFRA_LOG_LEVEL": "ERROR", "LOG_LEVEL": ""}, clear=False
    ):
        assert _resolve_log_level("INVALID") == "ERROR"


@pytest.mark.unit
def test_resolve_log_level_env_ai_infra_takes_precedence() -> None:
    """When no explicit level, AI_INFRA_LOG_LEVEL is used before LOG_LEVEL."""
    with patch.dict(
        os.environ, {"AI_INFRA_LOG_LEVEL": "WARNING", "LOG_LEVEL": "DEBUG"}, clear=False
    ):
        assert _resolve_log_level(None) == "WARNING"


@pytest.mark.unit
def test_configure_logging_does_not_raise() -> None:
    """configure_logging runs without error (may call structlog)."""
    configure_logging(level="INFO")
    # No assertion needed; we only check it doesn't raise


@pytest.mark.unit
def test_get_logger_without_crew_context_returns_logger() -> None:
    """get_logger_without_crew_context returns a callable logger-like object."""
    logger = get_logger_without_crew_context("test_component")
    assert logger is not None
    assert callable(getattr(logger, "info", None)) or hasattr(logger, "bind")


@pytest.mark.unit
def test_get_logger_returns_logger() -> None:
    """get_logger with component name returns logger-like object."""
    logger = get_logger("test_agent", tenant_id="t1", session_id="s1")
    assert logger is not None


@pytest.mark.unit
def test_event_span_success() -> None:
    """event_span context manager runs without error when block succeeds."""
    logger = get_logger_without_crew_context("test")
    start_payload = CrewRunStartEvent(operation="test")
    with event_span(logger, start_payload):
        pass


@pytest.mark.unit
def test_event_span_raises_and_logs() -> None:
    """event_span logs error and re-raises when block raises."""
    logger = get_logger_without_crew_context("test")
    start_payload = CrewRunStartEvent(operation="test")

    with pytest.raises(ValueError, match="expected"):
        with event_span(logger, start_payload):
            raise ValueError("expected")


@pytest.mark.unit
def test_mandatory_from_start() -> None:
    """_mandatory_from_start returns tenant_id, service_name, agent_id, session_id."""
    start = CrewRunStartEvent(
        tenant_id="t1", service_name="s1", agent_id="a1", session_id="sess1"
    )
    out = _mandatory_from_start(start)
    assert out["tenant_id"] == "t1"
    assert out["service_name"] == "s1"
    assert out["agent_id"] == "a1"
    assert out["session_id"] == "sess1"


@pytest.mark.unit
def test_make_end_payload_crew_run() -> None:
    """make_end_payload returns CrewRunEndEvent for CrewRunStartEvent."""
    start = CrewRunStartEvent(operation="run")
    end = make_end_payload(start, "success", 100, None)
    assert end.event_phase == "end"
    assert end.status == "success"
    assert end.duration_ms == 100


@pytest.mark.unit
def test_make_end_payload_database() -> None:
    """make_end_payload returns DatabaseEndEvent for DatabaseStartEvent."""
    start = DatabaseStartEvent(event="redis_connect", operation="connect")
    end = make_end_payload(start, "failure", 50, "TimeoutError")
    assert end.operation == "connect"
    assert end.event == "redis_connect"


@pytest.mark.unit
def test_make_end_payload_memory_load() -> None:
    """make_end_payload returns MemoryLoadEndEvent for MemoryLoadStartEvent."""
    start = MemoryLoadStartEvent(operation="prior_context")
    end = make_end_payload(start, "success", 10, None)
    assert end.event == "memory_load"


@pytest.mark.unit
def test_make_end_payload_memory_save() -> None:
    """make_end_payload returns MemorySaveEndEvent for MemorySaveStartEvent."""
    start = MemorySaveStartEvent(operation="save")
    end = make_end_payload(start, "success", 20, None)
    assert end.event == "memory_save"


@pytest.mark.unit
def test_make_end_payload_memory_search() -> None:
    """make_end_payload returns MemorySearchEndEvent for MemorySearchStartEvent."""
    start = MemorySearchStartEvent(operation="search")
    end = make_end_payload(start, "success", 5, None)
    assert end.event == "memory_search"


@pytest.mark.unit
def test_make_end_payload_unknown_type_raises() -> None:
    """make_end_payload raises TypeError for unknown start event type."""

    class UnknownStart:
        tenant_id = service_name = agent_id = session_id = "-"

    with pytest.raises(TypeError, match="Unknown start event type"):
        make_end_payload(UnknownStart(), "success", 0, None)  # type: ignore[arg-type]
