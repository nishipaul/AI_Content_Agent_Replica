"""
Load Langfuse keys (LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL) from Vault
and set them in environment variables.

Call load_langfuse_keys_from_vault() once before using Langfuse; no master_config checks.
The Vault path is read from the environment (e.g. langfuse_vault_path).
"""

from __future__ import annotations

import os


def load_langfuse_keys_from_vault(
    vault_path_env: str = "langfuse_vault_path",
    use_cache: bool = True,
) -> None:
    """
    Fetch Langfuse credentials from Vault and set them in os.environ.

    The Vault secret path is read from the environment (default: langfuse_vault_path).
    No master_config.yaml checks; keys are loaded with this single call.

    Vault secret may contain (any of these key names are accepted):
    - LANGFUSE_SECRET_KEY or secret_key or langfuse_secret_key
    - LANGFUSE_PUBLIC_KEY or public_key or langfuse_public_key
    - LANGFUSE_BASE_URL or base_url or langfuse_base_url

    After this call, os.getenv("LANGFUSE_SECRET_KEY"), os.getenv("LANGFUSE_PUBLIC_KEY"),
    and os.getenv("LANGFUSE_BASE_URL") will return the values from Vault (if present).

    Raises:
        ValueError: If vault path env is missing or secret is invalid.
    """
    vault_path = (os.getenv(vault_path_env) or vault_path_env or "").strip()
    if not vault_path:
        raise ValueError(
            f"Vault path for Langfuse credentials is required. Set the {vault_path_env!r} environment variable."
        )
    from ai_infra_vault.vault_client import VaultClient  # type: ignore[import-untyped]

    vault_client = VaultClient()
    secret = vault_client.get_secret(vault_path, use_cache=use_cache)
    if not secret:
        raise ValueError(
            f"Could not load Langfuse credentials from Vault path: {vault_path!r}"
        )

    secret_key = (
        secret.get("LANGFUSE_SECRET_KEY")
        or secret.get("secret_key")
        or secret.get("langfuse_secret_key")
    )
    public_key = (
        secret.get("LANGFUSE_PUBLIC_KEY")
        or secret.get("public_key")
        or secret.get("langfuse_public_key")
    )
    base_url = (
        secret.get("LANGFUSE_BASE_URL")
        or secret.get("LANGFUSE_HOST")
        or secret.get("base_url")
        or secret.get("langfuse_base_url")
    )

    if secret_key is not None and str(secret_key).strip():
        os.environ["LANGFUSE_SECRET_KEY"] = str(secret_key).strip()
    if public_key is not None and str(public_key).strip():
        os.environ["LANGFUSE_PUBLIC_KEY"] = str(public_key).strip()
    if base_url is not None and str(base_url).strip():
        os.environ["LANGFUSE_HOST"] = str(base_url).strip()
    if base_url is not None and str(base_url).strip():
        os.environ["LANGFUSE_BASE_URL"] = str(base_url).strip()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print(os.getenv("LANGFUSE_VAULT_PATH"))
    load_langfuse_keys_from_vault(
        vault_path_env=os.getenv("LANGFUSE_VAULT_PATH") or "langfuse_vault_path",
        use_cache=False,
    )
    print("LANGFUSE_SECRET_KEY set:", os.getenv("LANGFUSE_SECRET_KEY"))
    print("LANGFUSE_PUBLIC_KEY set:", os.getenv("LANGFUSE_PUBLIC_KEY"))
    print("LANGFUSE_BASE_URL set:", os.getenv("LANGFUSE_HOST", "(not set)"))
