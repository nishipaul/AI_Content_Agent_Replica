"""
PostgreSQL (SQL) connection via Vault credentials.

Returns a single shared connection when SQL is enabled in master_config.yaml.
Credentials are read from Vault using the path in the sql_vault_path environment variable.
Requires ai-infra-python-sdk-postgresql (or ai_infra_postgresql) and ai_infra_vault.

Raises SQLNotEnabledError if SQL is disabled; SQLVaultUnavailableError if the
vault path is missing or the secret cannot be loaded.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote_plus

from agent.utils.paths import BASE_DIR

_sql_connection: Any = None


class SQLNotEnabledError(Exception):
    """Raised when get_sql_connector() is called but SQL is not enabled in master_config."""


class SQLVaultUnavailableError(Exception):
    """Raised when the vault path for PostgreSQL is missing or vault secret could not be loaded."""

    def __init__(self, message: str = "PostgreSQL vault config unavailable") -> None:
        self.message = message
        super().__init__(message)


def _load_master_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load master_config.yaml. Default path: repo root / master_config.yaml."""
    if config_path is None:
        config_path = BASE_DIR.parent / "master_config.yaml"
    import yaml

    with open(config_path, "r") as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def _is_sql_enabled(master_config: dict[str, Any] | None = None) -> bool:
    """Return True if agent_runtime_config.databases.sql_enabled is true."""
    if master_config is None:
        master_config = _load_master_config()
    return (
        master_config.get("agent_runtime_config", {})
        .get("databases", {})
        .get("sql_enabled", False)
        is True
    )


def _build_pg_uri_from_secret(secret: dict[str, Any]) -> str | None:
    """
    Build a PostgreSQL connection URI from secret fields when no full URI is present.
    Returns postgresql://[user:password@]host[:port][/dbname] or None if host is missing.
    """
    host = (
        secret.get("host")
        or secret.get("POSTGRES_HOST")
        or secret.get("sql_host")
        or secret.get("server")
        or secret.get("hostname")
    )
    if not host or not str(host).strip():
        return None
    host = str(host).strip()

    port = secret.get("port") or secret.get("POSTGRES_PORT") or secret.get("sql_port")
    port_part = f":{port}" if port is not None and str(port).strip() else ""

    user = (
        secret.get("user")
        or secret.get("username")
        or secret.get("POSTGRES_USER")
        or secret.get("sql_user")
    )
    password = (
        secret.get("password")
        or secret.get("POSTGRES_PASSWORD")
        or secret.get("sql_password")
    )
    dbname = (
        secret.get("dbname")
        or secret.get("database")
        or secret.get("db")
        or secret.get("POSTGRES_DB")
        or secret.get("sql_database")
    )
    if user and str(user).strip():
        user_enc = quote_plus(str(user).strip())
        pass_enc = (
            quote_plus(str(password).strip())
            if password and str(password).strip()
            else ""
        )
        auth = f"{user_enc}:{pass_enc}@"
    else:
        auth = ""
    path = f"/{str(dbname).strip()}" if dbname and str(dbname).strip() else ""
    return f"postgresql://{auth}{host}{port_part}{path}"


def _get_connection() -> Any:
    """Return the shared PostgreSQL connection, initializing once from Vault using sql_vault_path env."""
    from ai_infra_vault.vault_client import VaultClient  # type: ignore[import-untyped]

    global _sql_connection
    if _sql_connection is None:
        config_path = BASE_DIR.parent / "master_config.yaml"
        master_config = _load_master_config(config_path)
        if not _is_sql_enabled(master_config):
            raise SQLNotEnabledError(
                "SQL is not enabled. Set agent_runtime_config.databases.sql_enabled to true in master_config.yaml."
            )

        vault_path_env = "SQL_VAULT_PATH"
        vault_path = (os.getenv(vault_path_env) or "").strip()
        if not vault_path:
            raise SQLVaultUnavailableError(
                f"Vault path for PostgreSQL is required. Set the {vault_path_env!r} environment variable."
            )

        vault_client = VaultClient()
        secret = vault_client.get_secret(vault_path, use_cache=True)
        if not secret:
            raise SQLVaultUnavailableError(
                f"Could not load PostgreSQL credentials from Vault path: {vault_path!r}"
            )

        connection_uri = (
            secret.get("connection_uri")
            or secret.get("DATABASE_URL")
            or secret.get("uri")
            or secret.get("connection_string")
            or secret.get("postgresql_uri")
        )
        if connection_uri:
            connection_uri = str(connection_uri).strip()
        if not connection_uri:
            connection_uri = _build_pg_uri_from_secret(secret)
        if not connection_uri:
            raise SQLVaultUnavailableError(
                f"PostgreSQL secret at {vault_path!r} must contain connection_uri/DATABASE_URL/uri, "
                "or host (and optionally port, user, password, dbname) to build URI."
            )

        dbname = (
            secret.get("dbname")
            or secret.get("database")
            or secret.get("db")
            or secret.get("POSTGRES_DB")
            or secret.get("sql_database")
        )
        dbname = str(dbname).strip() if dbname else None

        try:
            from ai_infra_postgresql.connections import (
                PostgreSQLConnection,  # type: ignore[import-untyped]
            )
        except ModuleNotFoundError:
            try:
                from ai_infra_python_sdk_postgresql.connections import (
                    PostgreSQLConnection,  # type: ignore[import-untyped]
                )
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    "PostgreSQL connection SDK not installed. Run: uv sync (requires ai-infra-python-sdk-postgresql)."
                ) from e

        _sql_connection = PostgreSQLConnection.initialize_from_vault(
            connection_uri=connection_uri,
            dbname=dbname,
        )
    return _sql_connection


def get_sql_connector() -> Any:
    """
    Return the shared PostgreSQL connection from the SDK.

    Requirements:
        - master_config.yaml must have agent_runtime_config.databases.sql_enabled: true.
        - Environment variable sql_vault_path must be set to the Vault path holding the secret.

    Vault secret keys (all optional except connection info):
        - connection_uri, DATABASE_URL, uri, connection_string, or postgresql_uri: Full URI; or
        - host (required to build URI), port, user/username, password, dbname/database/db.

    Returns:
        Connection object with .connector (PostgreSQLConnector) from the SDK.
        Use .connector.execute(query) for raw SQL or .connector.is_available() to check connectivity.

    Raises:
        SQLNotEnabledError: If sql_enabled is false in master_config.
        SQLVaultUnavailableError: If sql_vault_path is unset or the vault secret is invalid.
        ModuleNotFoundError: If ai-infra-python-sdk-postgresql is not installed.
    """
    return _get_connection()


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    conn = get_sql_connector()
    if not conn.connector.is_available():
        print(
            "Error: PostgreSQL connection failed (check credentials and network).",
            file=sys.stderr,
        )
        sys.exit(1)
    rows = conn.connector.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
        params=["public"],
    )
    print(rows)
