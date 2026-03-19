"""
Redis connection via Vault credentials.

Returns a single shared connection when Redis is enabled in master_config.yaml.
Credentials are read from Vault using the path in the redis_vault_path environment variable.
Requires ai-infra-python-sdk-core (Redis is part of core) and ai_infra_vault.

Raises RedisNotEnabledError if Redis is disabled; RedisVaultUnavailableError if the
vault path is missing or the secret cannot be loaded.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from agent.utils.paths import BASE_DIR

_redis_connection: Any = None


class RedisNotEnabledError(Exception):
    """Raised when get_redis_connector() is called but Redis is not enabled in master_config."""


class RedisVaultUnavailableError(Exception):
    """Raised when the vault path for Redis is missing or vault secret could not be loaded."""

    def __init__(self, message: str = "Redis vault config unavailable") -> None:
        self.message = message
        super().__init__(message)


def _load_master_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load master_config.yaml. Default path: repo root / master_config.yaml."""
    if config_path is None:
        config_path = BASE_DIR.parent / "master_config.yaml"
    import yaml

    with open(config_path, "r") as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def _is_redis_enabled(master_config: dict[str, Any] | None = None) -> bool:
    """Return True if agent_runtime_config.databases.redis_enabled is true."""
    if master_config is None:
        master_config = _load_master_config()
    return (
        master_config.get("agent_runtime_config", {})
        .get("databases", {})
        .get("redis_enabled", False)
        is True
    )


def _load_redis_credentials_from_vault() -> dict[str, Any]:
    """
    Load and parse Redis secret from Vault (redis_vault_path / REDIS_VAULT_PATH). Single place for Vault read.
    Returns normalized dict: host, port (int), password, username, key_prefix, cluster.
    Raises RedisVaultUnavailableError if vault path is missing or secret cannot be loaded.
    """
    from ai_infra_vault.vault_client import VaultClient  # type: ignore[import-untyped]

    vault_path_env = "redis_vault_path"
    vault_path = (
        os.getenv(vault_path_env) or os.getenv("REDIS_VAULT_PATH") or ""
    ).strip()
    if not vault_path:
        raise RedisVaultUnavailableError(
            f"Vault path for Redis is required. Set the {vault_path_env!r} environment variable."
        )
    vault_client = VaultClient()
    secret = vault_client.get_secret(vault_path, use_cache=True)
    if not secret:
        raise RedisVaultUnavailableError(
            f"Could not load Redis credentials from Vault path: {vault_path!r}"
        )
    host = (
        secret.get("host")
        or secret.get("redis_host")
        or secret.get("REDIS_CLOUD_HOST_URL")
        or secret.get("url")
    )
    if not host or not str(host).strip():
        raise RedisVaultUnavailableError(
            f"Redis secret at {vault_path!r} must contain host, redis_host, or REDIS_CLOUD_HOST_URL."
        )
    port = (
        secret.get("port") or secret.get("redis_port") or secret.get("REDIS_CLOUD_PORT")
    )
    try:
        port = int(port) if port is not None else 6379
    except (TypeError, ValueError):
        port = 6379
    password = (
        secret.get("password")
        or secret.get("redis_password")
        or secret.get("REDIS_CLOUD_PASSWORD")
    )
    username = secret.get("username") or secret.get("redis_username") or "default"
    key_prefix = secret.get("key_prefix") or secret.get("redis_key_prefix")
    cluster = secret.get("REDIS_USE_CLUSTER") or secret.get("redis_use_cluster")
    return {
        "host": str(host).strip(),
        "port": port,
        "password": (
            str(password).strip() if password and str(password).strip() else None
        ),
        "username": str(username).strip() if username else "default",
        "key_prefix": (
            str(key_prefix).strip() if key_prefix and str(key_prefix).strip() else None
        ),
        "cluster": str(cluster).strip() if cluster and str(cluster).strip() else None,
    }


def get_redis_credentials_from_vault() -> dict[str, Any]:
    """
    Load Redis credentials from Vault (redis_vault_path / REDIS_VAULT_PATH). No master_config check.
    Returns a dict suitable for AgentConfigConnection.initialize_from_vault(..., **credentials).
    Keys: redis_host, redis_port, redis_password, redis_username (and optionally redis_use_cluster).
    Raises RedisVaultUnavailableError if vault path is missing or secret cannot be loaded.
    """
    creds = _load_redis_credentials_from_vault()
    out: dict[str, Any] = {
        "redis_host": creds["host"],
        "redis_port": creds["port"],
        "redis_username": creds["username"],
    }
    if creds.get("password"):
        out["redis_password"] = creds["password"]
    if creds.get("cluster"):
        out["redis_use_cluster"] = creds["cluster"]
    return out


def get_redis_credentials_from_env() -> dict[str, Any]:
    """
    Build Redis credentials dict from environment (REDIS_HOST, REDIS_PORT, etc.). No master_config or Vault.
    Returns a dict suitable for AgentConfigConnection.initialize_from_vault(..., **credentials).
    """
    host = (os.getenv("REDIS_HOST") or os.getenv("redis_host") or "").strip()
    port_raw = os.getenv("REDIS_PORT") or os.getenv("redis_port")
    try:
        port = int(port_raw) if port_raw else 6379
    except (TypeError, ValueError):
        port = 6379
    password = (
        os.getenv("REDIS_PASSWORD") or os.getenv("redis_password") or ""
    ).strip() or None
    username = (
        os.getenv("REDIS_USER")
        or os.getenv("REDIS_USERNAME")
        or os.getenv("redis_username")
        or "default"
    ).strip()
    cluster = (
        os.getenv("REDIS_USE_CLUSTER") or os.getenv("redis_use_cluster") or ""
    ).strip() or None
    out: dict[str, Any] = {
        "redis_host": host or "localhost",
        "redis_port": port,
        "redis_username": username or "default",
    }
    if password:
        out["redis_password"] = password
    if cluster:
        out["redis_use_cluster"] = cluster
    return out


def _get_connection() -> Any:
    """Return the shared Redis connection, initializing once from Vault using redis_vault_path env."""
    global _redis_connection
    if _redis_connection is None:
        config_path = BASE_DIR.parent / "master_config.yaml"
        master_config = _load_master_config(config_path)
        if not _is_redis_enabled(master_config):
            raise RedisNotEnabledError(
                "Redis is not enabled. Set agent_runtime_config.databases.redis_enabled to true in master_config.yaml."
            )

        creds = _load_redis_credentials_from_vault()

        if creds.get("cluster"):
            os.environ.setdefault("REDIS_USE_CLUSTER", creds["cluster"])

        try:
            from ai_infra_python_sdk_core.ai_infra.connections import (
                RedisConnection,  # type: ignore[import-untyped]
            )
        except ModuleNotFoundError:
            try:
                from ai_infra_python_sdk_redis.connections import (
                    RedisConnection,  # type: ignore[import-untyped]
                )
            except ModuleNotFoundError:
                try:
                    from ai_infra_redis.connections import (
                        RedisConnection,  # type: ignore[import-untyped]
                    )
                except ModuleNotFoundError as e:
                    raise ModuleNotFoundError(
                        "Redis connection not available. Run: uv sync (requires ai-infra-python-sdk-core)."
                    ) from e

        kwargs: dict[str, Any] = {
            "host": creds["host"],
            "port": creds["port"],
            "username": creds["username"],
        }
        if creds.get("password"):
            kwargs["password"] = creds["password"]
        if creds.get("key_prefix"):
            kwargs["key_prefix"] = creds["key_prefix"]

        _redis_connection = RedisConnection.initialize_from_vault(**kwargs)
        # Core SDK exposes .connector (RedisConnector); attach .client for backward compatibility
        if not hasattr(_redis_connection, "client") and hasattr(
            _redis_connection, "connector"
        ):
            _redis_connection.client = getattr(
                _redis_connection.connector, "_client", None
            )
    return _redis_connection


def get_redis_connector() -> Any:
    """
    Return the shared Redis connection from the SDK.

    Requirements:
        - master_config.yaml must have agent_runtime_config.databases.redis_enabled: true.
        - Environment variable redis_vault_path must be set to the Vault path holding the secret.

    Vault secret keys (passed to RedisConnection.initialize_from_vault):
        - host, redis_host, REDIS_CLOUD_HOST_URL, or url: Redis host (required).
        - port, redis_port, or REDIS_CLOUD_PORT: Redis port.
        - password, redis_password, or REDIS_CLOUD_PASSWORD: Redis password.
        - username or redis_username: Redis username (default: "default").
        - key_prefix or redis_key_prefix: Optional key prefix.
        - REDIS_USE_CLUSTER or redis_use_cluster: Cluster flag (set in env for connector).

    Returns:
        Connection object with .connector (RedisConnector from ai_infra_python_sdk_core) and,
        when from core, .client (underlying redis.Redis or RedisCluster) for compatibility.

    Raises:
        RedisNotEnabledError: If redis_enabled is false in master_config.
        RedisVaultUnavailableError: If redis_vault_path is unset or the vault secret is invalid.
        ModuleNotFoundError: If ai-infra-python-sdk-core is not installed.
    """
    return _get_connection()


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    conn = get_redis_connector()
    if hasattr(conn, "connector") and not conn.connector.is_available():
        print(
            "Error: Redis connection failed (check credentials and network).",
            file=sys.stderr,
        )
        sys.exit(1)
    client = getattr(conn, "client", None)
    if client is not None:
        print("PING:", client.ping())
        client.close()
    else:
        conn.close()
