import os

os.environ["OTEL_SDK_DISABLED"] = "true"

import yaml
from ai_infra_python_sdk_core.ai_infra.prompt import (
    langfuse_prompt,  # type: ignore[import-untyped]
)

langfuse_vault = (
    os.getenv("langfuse_vault_path") or os.getenv("LANGFUSE_VAULT_PATH") or ""
).strip()
if langfuse_vault:
    os.environ.setdefault("langfuse_vault_path", langfuse_vault)
    try:
        from agent.db_connections.get_langfuse_keys import load_langfuse_keys_from_vault

        load_langfuse_keys_from_vault(
            vault_path_env="langfuse_vault_path", use_cache=False
        )
    except Exception as e:
        print(f"Error loading langfuse keys from vault: {e}")
        raise
else:
    # Sync Langfuse keys from env for SDKs that read from env
    for key in (
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL",
    ):
        val = os.getenv(key)
        if val is not None:
            os.environ.setdefault(key, val)
    if os.getenv("LANGFUSE_HOST") and not os.environ.get("LANGFUSE_BASE_URL"):
        os.environ.setdefault("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", ""))

from agent.utils.paths import BASE_DIR

agents_config = BASE_DIR / "agent/config/agents.yaml"
tasks_config = BASE_DIR / "agent/config/tasks.yaml"
prompt_config = BASE_DIR.parent / "master_config.yaml"


result = langfuse_prompt.create_prompts_in_langfuse_for_crewai(
    PROMPT_CONFIG_FILE=prompt_config,
    AGENT_CONFIG_FILE=agents_config,
    TASK_CONFIG_FILE=tasks_config,
)
