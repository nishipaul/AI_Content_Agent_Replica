"""
API constants tests: paths exist, default values are correct.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.api.constants import (
    AGENTS_CONFIG_PATH,
    DEFAULT_MODEL,
    KAFKA_BOOTSTRAP_SERVERS_DEFAULT,
    MASTER_CONFIG_PATH,
    ROUTER_PREFIX,
    TASKS_CONFIG_PATH,
    USE_CREWAI_EXTERNAL_MEMORY,
)


@pytest.mark.unit
def test_router_prefix() -> None:
    """ROUTER_PREFIX is the expected path."""
    assert ROUTER_PREFIX == "/v1/ai-content-agent"


@pytest.mark.unit
def test_default_model() -> None:
    """DEFAULT_MODEL is auto-route."""
    assert DEFAULT_MODEL == "auto-route"


@pytest.mark.unit
def test_master_config_path_exists() -> None:
    """MASTER_CONFIG_PATH points to a file that exists in repo."""
    assert isinstance(MASTER_CONFIG_PATH, Path)
    assert MASTER_CONFIG_PATH.exists()
    assert MASTER_CONFIG_PATH.name == "master_config.yaml"


@pytest.mark.unit
def test_agents_and_tasks_config_paths() -> None:
    """AGENTS_CONFIG_PATH and TASKS_CONFIG_PATH are under agent config."""
    assert "agent" in str(AGENTS_CONFIG_PATH)
    assert "agent" in str(TASKS_CONFIG_PATH)
    assert AGENTS_CONFIG_PATH.name == "agents.yaml"
    assert TASKS_CONFIG_PATH.name == "tasks.yaml"


@pytest.mark.unit
def test_kafka_defaults() -> None:
    """Kafka default bootstrap is localhost:9092."""
    assert KAFKA_BOOTSTRAP_SERVERS_DEFAULT == "localhost:9092"


@pytest.mark.unit
def test_use_crewai_external_memory_is_bool() -> None:
    """USE_CREWAI_EXTERNAL_MEMORY is set from config (bool)."""
    assert isinstance(USE_CREWAI_EXTERNAL_MEMORY, bool)
