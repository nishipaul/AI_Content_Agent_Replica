"""
Load Redis keys (REDIS_URL, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, etc.) from Vault
and set them in environment variables.

Call load_redis_keys_from_vault() once before using Redis; no master_config checks.
The Vault path is read from the environment (e.g. redis_vault_path).
"""

from __future__ import annotations

import os


def load_redis_keys_from_vault(
    vault_path_env: str = "redis_vault_path",
    use_cache: bool = True,
) -> None:
    """
    Fetch Redis credentials from Vault and set them in os.environ.

    The Vault secret path is read from the environment (default: redis_vault_path).
    No master_config.yaml checks; keys are loaded with this single call.

    Vault secret may contain (any of these key names are accepted):
    - redis_url or url or connection_string -> REDIS_URL
    - host or redis_host -> REDIS_HOST
    - port or redis_port -> REDIS_PORT
    - password or redis_password -> REDIS_PASSWORD
    - username or redis_username -> REDIS_USERNAME
    - db or database or redis_db -> REDIS_DB
    - ssl or redis_ssl -> REDIS_SSL

    After this call, os.getenv("REDIS_URL"), os.getenv("REDIS_HOST"), etc.
    will return the values from Vault (if present).

    Raises:
        ValueError: If vault path env is missing or secret is invalid.
    """
    vault_path = (os.getenv(vault_path_env) or vault_path_env or "").strip()
    if not vault_path:
        raise ValueError(
            f"Vault path for Redis credentials is required. Set the {vault_path_env!r} environment variable."
        )
    from ai_infra_vault.vault_client import VaultClient  # type: ignore[import-untyped]

    vault_client = VaultClient()
    secret = vault_client.get_secret(vault_path, use_cache=use_cache)
    if not secret:
        raise ValueError(
            f"Could not load Redis credentials from Vault path: {vault_path!r}"
        )

    host = (
        secret.get("host")
        or secret.get("redis_host")
        or secret.get("REDIS_CLOUD_HOST_URL")
        or secret.get("url")
    )
    port = secret.get("REDIS_CLOUD_PORT") or secret.get("redis_port")
    password = secret.get("REDIS_CLOUD_PASSWORD") or secret.get("redis_password")
    username = secret.get("username") or secret.get("redis_username") or "default"
    db = (
        secret.get("db")
        or secret.get("database")
        or secret.get("redis_db")
        or "ai_platform_memory"
    )
    cluster = secret.get("REDIS_USE_CLUSTER") or 0

    if host is not None and str(host).strip():
        os.environ["redis_host"] = str(host).strip()
    if port is not None:
        os.environ["redis_port"] = str(int(port))
    if password is not None and str(password).strip():
        os.environ["redis_password"] = str(password).strip()
    if username is not None and str(username).strip():
        os.environ["redis_username"] = str(username).strip()
    if db is not None:
        os.environ["redis_database"] = str(db)
    if cluster is not None:
        os.environ["REDIS_USE_CLUSTER"] = str(cluster)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    load_redis_keys_from_vault(
        vault_path_env=os.getenv("REDIS_VAULT_PATH") or "redis_vault_path",
        use_cache=False,
    )
    print("redis_host set:", os.getenv("redis_host", "(not set)"))
    print("redis_port set:", os.getenv("redis_port", "(not set)"))
    print("redis_password set:", os.getenv("redis_password"))
    print("redis_username set:", os.getenv("redis_username", "(not set)"))
    print("redis_database set:", os.getenv("redis_database", "(not set)"))
    print("REDIS_USE_CLUSTER set:", os.getenv("REDIS_USE_CLUSTER", "(not set)"))
