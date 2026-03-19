"""
Module to check if the tenant is registered in the agent config and agent is enabled for the tenant.
Uses a single shared AgentConfigConnection (from ai_infra_python_sdk_agent_config) for all calls.
AI config URL from env (AI_CONFIG_API_BASE_URL_DEFAULT); Redis credentials from Vault (redis_vault_path) or env.
No master_config. AgentConfigConnection is given Redis credentials (redis_host, redis_port, etc.), not a connection.
"""

import os
from typing import Any

from agent.api.constants import AI_CONFIG_API_BASE_URL_DEFAULT

_connection: Any = None


def _ai_config_base_url_or_none() -> str | None:
    """Single URL for AI Config API from env, stripped, or None."""
    raw = (
        os.getenv("AI_CONFIG_API_BASE_URL")
        or os.getenv("AI_CONFIG_API_URL")
        or os.getenv("ai_config_api_base_url")
        or AI_CONFIG_API_BASE_URL_DEFAULT
    )
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip().rstrip("/")


class TenantConfigUnavailableError(Exception):
    """Raised when the agent-config SDK is not installed or vault/connection fails."""

    def __init__(self, message: str = "Tenant config service unavailable") -> None:
        self.message = message
        super().__init__(message)


def _get_redis_credentials() -> dict[str, Any]:
    """Redis credentials from Vault (redis_vault_path) or from env. No master_config."""
    from agent.db_connections.get_redis_connector import (
        RedisVaultUnavailableError,
        get_redis_credentials_from_env,
        get_redis_credentials_from_vault,
    )

    try:
        return get_redis_credentials_from_vault()
    except RedisVaultUnavailableError:
        return get_redis_credentials_from_env()


def _get_connection() -> Any:
    """Return the shared AgentConfigConnection, initializing once with AI config URL from env (AI_CONFIG_API_BASE_URL_DEFAULT) and Redis credentials."""
    try:
        from ai_infra_python_sdk_agent_config import (
            AgentConfigConnection,  # type: ignore[import-untyped]
        )
    except ModuleNotFoundError:
        try:
            from ai_infra_agent_config import (
                AgentConfigConnection,  # type: ignore[import-untyped]
            )
        except ModuleNotFoundError as e:
            raise TenantConfigUnavailableError(
                "Agent config SDK not installed. Add dependency ai-infra-python-sdk-agent-config in pyproject.toml and run: uv sync"
            ) from e

    global _connection
    if _connection is None:
        ai_config_url: str | None = _ai_config_base_url_or_none()
        redis_credentials = _get_redis_credentials()
        kwargs: dict[str, Any] = {
            "ai_config_url": ai_config_url,
            **redis_credentials,
        }
        _connection = AgentConfigConnection.initialize_from_vault(**kwargs)
    return _connection


async def tenant_exists(smtip_tid: str, smtip_feature: str) -> bool:
    """Check if the tenant is registered and agent is enabled. Uses the shared connection."""
    connection = _get_connection()
    return bool(await connection.client.get_config(smtip_tid, smtip_feature))
