"""
Kafka pipeline tests: _kafka_bootstrap_servers, _is_kafka_enabled, parse/serialization.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from agent.api.kafka_pipeline import (
    _build_envelope,
    _get_consumer_agent_id,
    _get_consumer_group_id,
    _get_max_poll_interval_ms,
    _get_processing_timeout_seconds,
    _is_kafka_enabled,
    _kafka_bootstrap_servers,
    _load_master_config,
    _make_ssl_context_no_verify,
    _normalized_env_suffix,
    _parse_envelope,
    start_kafka_pipeline_thread,
)


@pytest.mark.unit
def test_kafka_bootstrap_servers_from_env() -> None:
    """_kafka_bootstrap_servers uses KAFKA_BOOTSTRAP_ADDRESS when set."""
    with patch.dict(
        os.environ, {"KAFKA_BOOTSTRAP_ADDRESS": "broker:9092"}, clear=False
    ):
        assert _kafka_bootstrap_servers() == "broker:9092"


@pytest.mark.unit
def test_kafka_bootstrap_servers_default() -> None:
    """_kafka_bootstrap_servers returns localhost:9092 when no env set."""
    with patch.dict(
        os.environ,
        {"KAFKA_BOOTSTRAP_ADDRESS": "", "KAFKA_URL": "", "kafka_bootstrap_address": ""},
        clear=False,
    ):
        # Clear so fallback to default
        orig = os.environ.get("KAFKA_BOOTSTRAP_ADDRESS")
        orig2 = os.environ.get("KAFKA_URL")
        try:
            os.environ.pop("KAFKA_BOOTSTRAP_ADDRESS", None)
            os.environ.pop("KAFKA_URL", None)
            os.environ.pop("kafka_bootstrap_address", None)
            assert _kafka_bootstrap_servers() == "localhost:9092"
        finally:
            if orig is not None:
                os.environ["KAFKA_BOOTSTRAP_ADDRESS"] = orig
            if orig2 is not None:
                os.environ["KAFKA_URL"] = orig2


@pytest.mark.unit
def test_is_kafka_enabled_reads_config() -> None:
    """_is_kafka_enabled returns bool from master_config."""
    v = _is_kafka_enabled()
    assert isinstance(v, bool)


@pytest.mark.unit
def test_parse_envelope() -> None:
    """_parse_envelope extracts agent_id, correlation_id and payload from envelope."""
    envelope = {
        "agent_id": "my-agent",
        "correlation_id": "cid-123",
        "data": {
            "locale": "en-US",
            "smtip_tid": "t",
            "smtip_feature": "f",
            "model": "m",
        },
    }
    raw = json.dumps(envelope).encode("utf-8")
    agent_id, cid, payload = _parse_envelope(raw)
    assert agent_id == "my-agent"
    assert cid == "cid-123"
    assert payload.get("smtip_tid") == "t"


@pytest.mark.unit
def test_parse_envelope_missing_agent_id_raises() -> None:
    """_parse_envelope raises ValueError when agent_id missing."""
    raw = json.dumps({"data": {"smtip_tid": "t"}}).encode("utf-8")
    with pytest.raises(ValueError, match="agent_id"):
        _parse_envelope(raw)


@pytest.mark.unit
def test_build_envelope() -> None:
    """_build_envelope returns dict with agent_id, correlation_id, data."""
    out = _build_envelope("agent-1", "corr-1", {"key": "value"})
    assert out["agent_id"] == "agent-1"
    assert out["correlation_id"] == "corr-1"
    assert out["data"] == {"key": "value"}


@pytest.mark.unit
def test_normalized_env_suffix() -> None:
    """_normalized_env_suffix normalizes to uppercase safe string."""
    assert _normalized_env_suffix("my-agent") == "MY_AGENT"
    assert _normalized_env_suffix("  a b c  ") == "A_B_C"


@pytest.mark.unit
def test_make_ssl_context_no_verify() -> None:
    """_make_ssl_context_no_verify returns SSL context with verification disabled."""
    import ssl

    ctx = _make_ssl_context_no_verify()
    assert ctx is not None
    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_NONE


@pytest.mark.unit
def test_process_one_message_async_returns_success_when_crew_mocked() -> None:
    """_process_one_message_async returns success response when tenant valid and crew is mocked."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from tests.conftest import _mock_crew_result

    async def _mock_run(_inputs):
        return _mock_crew_result()

    payload = {
        "locale": "en-US",
        "survey_data": {"survey_id": "s", "responses": []},
        "smtip_tid": "t",
        "smtip_feature": "f",
        "model": "auto-route",
    }
    envelope = {
        "agent_id": "ai-content-agent",
        "correlation_id": "corr-1",
        "data": payload,
    }
    raw = json.dumps(envelope).encode("utf-8")
    from agent.api.kafka_pipeline import _process_one_message_async

    with (
        patch(
            "agent.api.tenant.tenant_exists", new_callable=AsyncMock, return_value=True
        ),
        patch("agent.api.agent_service.run_agentic_crew", side_effect=_mock_run),
    ):
        result = asyncio.run(_process_one_message_async(raw))
    assert result["success"] is True
    assert "content" in result
    assert result["content"]["summary"] == "[MOCK] Survey summary for testing."
    assert "latency_seconds" in result


@pytest.mark.unit
def test_load_master_config() -> None:
    """_load_master_config returns dict with agent_registry_config."""
    config = _load_master_config()
    assert isinstance(config, dict)
    assert "agent_registry_config" in config
    assert "agent_runtime_config" in config


@pytest.mark.unit
def test_get_consumer_agent_id_from_env() -> None:
    """_get_consumer_agent_id uses KAFKA_CONSUMER_AGENT_ID when set."""
    with patch.dict(
        os.environ, {"KAFKA_CONSUMER_AGENT_ID": "my-kafka-agent"}, clear=False
    ):
        assert _get_consumer_agent_id() == "my-kafka-agent"


@pytest.mark.unit
def test_get_consumer_agent_id_from_master_config() -> None:
    """_get_consumer_agent_id falls back to master_config when env not set."""
    with patch.dict(
        os.environ,
        {"KAFKA_CONSUMER_AGENT_ID": ""},
        clear=False,
    ):
        # Should read from _load_master_config (master_config has agent_id)
        result = _get_consumer_agent_id()
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
def test_get_consumer_group_id_default() -> None:
    """_get_consumer_group_id returns agent_id-consumer-group when env not set."""
    # Remove env vars so fallback f"{agent_id}-consumer-group" is used
    saved = {
        k: os.environ.pop(k, None)
        for k in ("KAFKA_GROUP_ID", "KAFKA_GROUP_ID_MY_AGENT")
    }
    try:
        assert _get_consumer_group_id("my-agent") == "my-agent-consumer-group"
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


@pytest.mark.unit
def test_get_consumer_group_id_from_env() -> None:
    """_get_consumer_group_id uses KAFKA_GROUP_ID when set."""
    with patch.dict(os.environ, {"KAFKA_GROUP_ID": "custom-group"}, clear=False):
        assert _get_consumer_group_id("any-agent") == "custom-group"


@pytest.mark.unit
def test_get_max_poll_interval_ms_default() -> None:
    """_get_max_poll_interval_ms returns int >= 1000."""
    v = _get_max_poll_interval_ms("agent1", "group1")
    assert isinstance(v, int)
    assert v >= 1000


@pytest.mark.unit
def test_get_max_poll_interval_ms_from_env() -> None:
    """_get_max_poll_interval_ms uses MAX_POLL_INTERVAL_MS when set."""
    with patch.dict(os.environ, {"MAX_POLL_INTERVAL_MS": "120000"}, clear=False):
        v = _get_max_poll_interval_ms("a", "g")
        assert v == 120000


@pytest.mark.unit
def test_get_processing_timeout_seconds() -> None:
    """_get_processing_timeout_seconds returns int >= 1."""
    v = _get_processing_timeout_seconds(600000, "a", "g")
    assert isinstance(v, int)
    assert v >= 1


@pytest.mark.unit
def test_start_kafka_pipeline_thread_returns_none_when_disabled() -> None:
    """start_kafka_pipeline_thread returns None when kafka_enabled is False."""
    with patch("agent.api.kafka_pipeline._is_kafka_enabled", return_value=False):
        t = start_kafka_pipeline_thread()
    assert t is None


@pytest.mark.unit
def test_start_kafka_pipeline_thread_returns_thread_when_enabled() -> None:
    """start_kafka_pipeline_thread returns Thread when kafka_enabled is True."""
    with patch("agent.api.kafka_pipeline._is_kafka_enabled", return_value=True):
        t = start_kafka_pipeline_thread()
    assert t is not None
    assert t.name == "kafka-pipeline"
    assert t.daemon is True
