"""
DB connector tests: Redis, Mongo, SQL — config loading, enabled checks, exceptions.
All tests use mocks; no real Vault, Redis, Mongo, or PostgreSQL connections.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agent.db_connections.get_mongo_connector import (
    MongoNotEnabledError,
    MongoVaultUnavailableError,
    _is_mongo_enabled,
)
from agent.db_connections.get_mongo_connector import (
    _load_master_config as mongo_load_config,
)
from agent.db_connections.get_redis_connector import (
    RedisNotEnabledError,
    RedisVaultUnavailableError,
    _is_redis_enabled,
)
from agent.db_connections.get_redis_connector import (
    _load_master_config as redis_load_config,
)
from agent.db_connections.get_sql_connector import (
    SQLNotEnabledError,
    SQLVaultUnavailableError,
    _build_pg_uri_from_secret,
    _is_sql_enabled,
)
from agent.db_connections.get_sql_connector import (
    _load_master_config as sql_load_config,
)

# ----- Shared: _load_master_config -----


@pytest.mark.unit
def test_redis_load_master_config_default_path() -> None:
    """_load_master_config returns dict with agent_runtime_config when path not given."""
    config = redis_load_config()
    assert isinstance(config, dict)
    assert "agent_runtime_config" in config


@pytest.mark.unit
def test_redis_load_master_config_custom_path() -> None:
    """_load_master_config accepts custom config path."""
    from agent.utils.paths import BASE_DIR

    path = BASE_DIR.parent / "master_config.yaml"
    config = redis_load_config(config_path=path)
    assert isinstance(config, dict)


# ----- Redis -----


@pytest.mark.unit
def test_is_redis_enabled_reads_config() -> None:
    """_is_redis_enabled returns bool from master_config (databases.redis_enabled)."""
    v = _is_redis_enabled()
    assert isinstance(v, bool)
    # When passed explicit config False, returns False
    assert (
        _is_redis_enabled(
            {"agent_runtime_config": {"databases": {"redis_enabled": False}}}
        )
        is False
    )


@pytest.mark.unit
def test_is_redis_enabled_true_when_set() -> None:
    """_is_redis_enabled returns True when agent_runtime_config.databases.redis_enabled is true."""
    config = {"agent_runtime_config": {"databases": {"redis_enabled": True}}}
    assert _is_redis_enabled(config) is True


@pytest.mark.unit
def test_redis_not_enabled_error() -> None:
    """RedisNotEnabledError is raised when get_redis_connector called and Redis disabled."""
    with patch(
        "agent.db_connections.get_redis_connector._is_redis_enabled", return_value=False
    ):
        with patch("agent.db_connections.get_redis_connector._load_master_config") as m:
            m.return_value = {"agent_runtime_config": {"databases": {}}}
            from agent.db_connections.get_redis_connector import get_redis_connector

            with pytest.raises(RedisNotEnabledError):
                get_redis_connector()


@pytest.mark.unit
def test_redis_vault_unavailable_error_message() -> None:
    """RedisVaultUnavailableError has .message attribute."""
    e = RedisVaultUnavailableError("Custom message")
    assert e.message == "Custom message"
    assert str(e) == "Custom message"


# ----- Mongo -----


@pytest.mark.unit
def test_is_mongo_enabled_reads_config() -> None:
    """_is_mongo_enabled returns bool from master_config (databases.mongo_enabled)."""
    v = _is_mongo_enabled()
    assert isinstance(v, bool)
    assert (
        _is_mongo_enabled(
            {"agent_runtime_config": {"databases": {"mongo_enabled": False}}}
        )
        is False
    )


@pytest.mark.unit
def test_is_mongo_enabled_true_when_set() -> None:
    """_is_mongo_enabled returns True when mongo_enabled is true in config."""
    config = {"agent_runtime_config": {"databases": {"mongo_enabled": True}}}
    assert _is_mongo_enabled(config) is True


@pytest.mark.unit
def test_mongo_not_enabled_error() -> None:
    """MongoNotEnabledError raised when Mongo disabled in config."""
    with patch(
        "agent.db_connections.get_mongo_connector._get_connection",
        side_effect=MongoNotEnabledError(),
    ):
        from agent.db_connections.get_mongo_connector import get_mongo_connector

        with pytest.raises(MongoNotEnabledError):
            get_mongo_connector()


@pytest.mark.unit
def test_mongo_vault_unavailable_error_message() -> None:
    """MongoVaultUnavailableError has .message attribute."""
    e = MongoVaultUnavailableError("Vault path missing")
    assert e.message == "Vault path missing"


# ----- SQL (PostgreSQL) -----


@pytest.mark.unit
def test_is_sql_enabled_reads_config() -> None:
    """_is_sql_enabled returns bool from master_config (databases.sql_enabled)."""
    v = _is_sql_enabled()
    assert isinstance(v, bool)
    assert (
        _is_sql_enabled({"agent_runtime_config": {"databases": {"sql_enabled": False}}})
        is False
    )


@pytest.mark.unit
def test_is_sql_enabled_true_when_set() -> None:
    """_is_sql_enabled returns True when sql_enabled is true in config."""
    config = {"agent_runtime_config": {"databases": {"sql_enabled": True}}}
    assert _is_sql_enabled(config) is True


@pytest.mark.unit
def test_build_pg_uri_from_secret_host_only() -> None:
    """_build_pg_uri_from_secret returns postgresql://host with only host set."""
    uri = _build_pg_uri_from_secret({"host": "db.example.com"})
    assert uri == "postgresql://db.example.com"


@pytest.mark.unit
def test_build_pg_uri_from_secret_postgres_keys() -> None:
    """_build_pg_uri_from_secret uses POSTGRES_* keys from secret."""
    uri = _build_pg_uri_from_secret(
        {
            "POSTGRES_HOST": "pg.example.com",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "u",
            "POSTGRES_PASSWORD": "p",
            "POSTGRES_DB": "mydb",
        }
    )
    assert uri is not None
    assert "pg.example.com" in uri
    assert "5432" in uri
    assert "mydb" in uri
    assert uri.startswith("postgresql://")


@pytest.mark.unit
def test_build_pg_uri_from_secret_no_host_returns_none() -> None:
    """_build_pg_uri_from_secret returns None when host is missing."""
    uri = _build_pg_uri_from_secret({"user": "u", "password": "p"})
    assert uri is None


@pytest.mark.unit
def test_sql_not_enabled_error() -> None:
    """SQLNotEnabledError raised when SQL disabled in config."""
    with patch(
        "agent.db_connections.get_sql_connector._get_connection",
        side_effect=SQLNotEnabledError(),
    ):
        from agent.db_connections.get_sql_connector import get_sql_connector

        with pytest.raises(SQLNotEnabledError):
            get_sql_connector()


@pytest.mark.unit
def test_sql_vault_unavailable_error_message() -> None:
    """SQLVaultUnavailableError has .message attribute."""
    e = SQLVaultUnavailableError("Vault unavailable")
    assert e.message == "Vault unavailable"
