"""
MongoDB connection via Vault credentials.

Returns a single shared connection when Mongo is enabled in master_config.yaml.
Credentials are read from Vault using the path in the mongo_vault_path environment variable.
Requires ai-infra-python-sdk-mongodb (or ai_infra_mongodb) and ai_infra_vault.

Raises MongoNotEnabledError if mongo is disabled; MongoVaultUnavailableError if the
vault path is missing or the secret cannot be loaded.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote_plus

from agent.utils.paths import BASE_DIR

_mongo_connection: Any = None


class MongoNotEnabledError(Exception):
    """Raised when get_mongo_connector() is called but Mongo is not enabled in master_config."""


class MongoVaultUnavailableError(Exception):
    """Raised when the vault path for MongoDB is missing or vault secret could not be loaded."""

    def __init__(self, message: str = "MongoDB vault config unavailable") -> None:
        self.message = message
        super().__init__(message)


def _load_master_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load master_config.yaml. Default path: repo root / master_config.yaml."""
    if config_path is None:
        config_path = BASE_DIR.parent / "master_config.yaml"
    import yaml

    with open(config_path, "r") as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def _is_mongo_enabled(master_config: dict[str, Any] | None = None) -> bool:
    """Return True if agent_runtime_config.databases.mongo_enabled is true."""
    if master_config is None:
        master_config = _load_master_config()
    return (
        master_config.get("agent_runtime_config", {})
        .get("databases", {})
        .get("mongo_enabled", False)
        is True
    )


def _get_connection() -> Any:
    """Return the shared MongoDB connection, initializing once from Vault using mongo_vault_path env."""
    from ai_infra_vault.vault_client import VaultClient  # type: ignore[import-untyped]

    global _mongo_connection
    if _mongo_connection is None:
        config_path = BASE_DIR.parent / "master_config.yaml"
        master_config = _load_master_config(config_path)
        if not _is_mongo_enabled(master_config):
            raise MongoNotEnabledError(
                "Mongo is not enabled. Set agent_runtime_config.databases.mongo_enabled to true in master_config.yaml."
            )

        vault_path_env = "MONGO_VAULT_PATH"
        vault_path = (os.getenv(vault_path_env) or "").strip()
        if not vault_path:
            raise MongoVaultUnavailableError(
                f"Vault path for MongoDB is required. Set the {vault_path_env!r} environment variable."
            )

        vault_client = VaultClient()
        secret = vault_client.get_secret(vault_path, use_cache=True)
        if not secret:
            raise MongoVaultUnavailableError(
                f"Could not load MongoDB credentials from Vault path: {vault_path!r}"
            )

        host = secret.get("host") or secret.get("mongo_host")
        _port = secret.get("port") or secret.get("mongo_port", 27017)  # noqa: F841
        username = secret.get("username") or secret.get("mongo_username")
        password = secret.get("password") or secret.get("mongo_password")
        database = secret.get("database") or secret.get("mongo_database")

        host_url = host.replace("DB_USER_NAME", username).replace(
            "DB_PASSWORD", password
        )
        try:
            from ai_infra_mongodb.connections import (
                MongoDBConnection,  # type: ignore[import-untyped]
            )
        except ModuleNotFoundError:
            try:
                from ai_infra_python_sdk_mongodb.connections import (
                    MongoDBConnection,  # type: ignore[import-untyped]
                )
            except ModuleNotFoundError:
                try:
                    from ai_infra_python_sdk_mongodb.connections import (
                        MongoConnection as MongoDBConnection,  # type: ignore[import-untyped]
                    )
                except ModuleNotFoundError as e:
                    raise ModuleNotFoundError(
                        "MongoDB connection SDK not installed. Run: uv sync (requires ai-infra-python-sdk-mongodb)."
                    ) from e

        _mongo_connection = MongoDBConnection.initialize_from_vault(
            connection_uri=host_url,
            database=database,
        )
    return _mongo_connection


def get_mongo_connector() -> Any:
    """
    Return the shared MongoDB connection from the SDK.

    Requirements:
        - master_config.yaml must have agent_runtime_config.databases.mongo_enabled: true.
        - Environment variable mongo_vault_path must be set to the Vault path holding the secret.

    Vault secret keys (all optional except host/connection info):
        - host or mongo_host: Hostname or URI. May contain placeholders DB_USER_NAME and
          DB_PASSWORD, which are replaced with the username and password from the secret.
        - port or mongo_port: Port (default 27017).
        - username or mongo_username: MongoDB username.
        - password or mongo_password: MongoDB password.
        - database or mongo_database: Default database name.

    Returns:
        Connection object with:
            - .connector.client: pymongo MongoClient (or None if connection failed).
            - .connector.db: pymongo Database for the default database.

    Raises:
        MongoNotEnabledError: If mongo_enabled is false in master_config.
        MongoVaultUnavailableError: If mongo_vault_path is unset or the vault secret is invalid.
        ModuleNotFoundError: If ai-infra-python-sdk-mongodb is not installed.
    """
    return _get_connection()


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    conn = get_mongo_connector()
    client = conn.connector.client
    db = conn.connector.db
    if client is None:
        print(
            "Error: MongoDB connection failed (check credentials, authSource, and network).",
            file=sys.stderr,
        )
        sys.exit(1)
    if db is not None and hasattr(db, "list_collection_names"):
        print("Collections:", db.list_collection_names())
    else:
        print("Client:", client)
