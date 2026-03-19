"""
Production-ready FastAPI layer for CrewAI agents.

- RESTful endpoints under /api/v1
- Async/await with non-blocking crew execution (asyncio.to_thread)
- Request/response validation via Pydantic
- Central error handling and RFC 7807–style error responses
- WebSocket support for real-time survey-summary at /api/v1/ws/survey-summary
"""

# from __future__ import annotations

import os
import warnings

import yaml

from agent.utils.logging_config import (
    configure_logging,
    get_logger_without_crew_context,
)

# Configure structlog once at app load (boilerplate strategy)
configure_logging()

# Ensure Langfuse tracing env is set for SDKs that read it from os.environ
os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", os.getenv("ENVIRONMENT", "dev"))

# Sync Redis and AI Config to os.environ so SDK (AgentConfigConnection.initialize_from_env) sees them
for env_key, src_key in [
    ("REDIS_HOST", "redis_host"),
    ("REDIS_PORT", "redis_port"),
    ("REDIS_PASSWORD", "redis_password"),
    ("REDIS_USER", "redis_username"),
    ("REDIS_USE_CLUSTER", "redis_use_cluster"),
]:
    val = os.getenv(src_key) or os.getenv(env_key)
    if val and str(val).strip():
        os.environ.setdefault(env_key, str(val).strip())
ai_config_url = (
    (
        os.getenv("AI_CONFIG_API_BASE_URL")
        or os.getenv("AI_CONFIG_API_URL")
        or os.getenv("ai_config_api_base_url")
        or ""
    )
    .strip()
    .rstrip("/")
)
if ai_config_url:
    os.environ.setdefault("AI_CONFIG_API_URL", ai_config_url)

try:
    langfuse_vault = (
        os.getenv("langfuse_vault_path") or os.getenv("LANGFUSE_VAULT_PATH") or ""
    ).strip()
    if langfuse_vault:
        os.environ.setdefault("langfuse_vault_path", langfuse_vault)
        from agent.db_connections.get_langfuse_keys import load_langfuse_keys_from_vault

        load_langfuse_keys_from_vault(
            vault_path_env="langfuse_vault_path", use_cache=False
        )
except ModuleNotFoundError as e:
    if "ai_infra_python_sdk_vault" in str(e) or "ai_infra_vault" in str(e):
        get_logger_without_crew_context("api").warning(
            "vault_sdk_not_installed",
            message="Run uv sync. Skipping Langfuse keys from vault.",
        )
    else:
        raise
except Exception as e:
    get_logger_without_crew_context("api").warning(
        "langfuse_vault_load_error", error=str(e)
    )

try:
    redis_vault = (
        os.getenv("redis_vault_path") or os.getenv("REDIS_VAULT_PATH") or ""
    ).strip()
    if redis_vault:
        os.environ.setdefault("redis_vault_path", redis_vault)
        from agent.db_connections.get_redis_keys import load_redis_keys_from_vault

        load_redis_keys_from_vault(vault_path_env="redis_vault_path", use_cache=False)
except ModuleNotFoundError as e:
    if "ai_infra_python_sdk_vault" in str(e) or "ai_infra_vault" in str(e):
        get_logger_without_crew_context("api").warning(
            "vault_sdk_not_installed",
            message="Run uv sync. Skipping Redis keys from vault.",
        )
    else:
        raise
except Exception as e:
    get_logger_without_crew_context("api").warning(
        "redis_vault_load_error", error=str(e)
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.api.constants import DOCS_PREFIX
from agent.api.exceptions import register_exception_handlers
from agent.api.kafka_pipeline import start_kafka_pipeline_thread
from agent.api.routes import router as v1_router
from agent.api.schemas import HealthResponse, ProbeResponse

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


docs_url = f"/v1/{DOCS_PREFIX}/docs"
openapi_url = f"/v1/{DOCS_PREFIX}/openapi.json"
redoc_url = f"/v1/{DOCS_PREFIX}/redoc"

# agent name from master_config.yaml
from agent.api.constants import MASTER_CONFIG_PATH

with open(MASTER_CONFIG_PATH, "r") as f:
    master_config = yaml.safe_load(f)
AGENT_NAME = master_config.get("agent_registry_config", {}).get(
    "name", "AI Infra Agent Example"
)
AGENT_DESCRIPTION = master_config.get("agent_registry_config", {}).get(
    "description", "AI Infra Agent Example"
)

app = FastAPI(
    title=AGENT_NAME,
    description=(AGENT_DESCRIPTION),
    version="1.0.0",
    docs_url=docs_url,
    openapi_url=openapi_url,
    redoc_url=redoc_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(v1_router)

# Start Kafka consumer on a separate thread when kafka_enabled in master_config
start_kafka_pipeline_thread()


@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
def root_health() -> HealthResponse:
    """Health at root for load balancers (same as /api/v1/health)."""
    return HealthResponse(
        service=AGENT_NAME,
        status="healthy",
        version="1.0.0",
    )


# Kubernetes probes (root paths match helm-values for kubelet)
@app.get("/startUpProbe", response_model=ProbeResponse)
@app.get("/readinessProbe", response_model=ProbeResponse)
@app.get("/livenessProbe", response_model=ProbeResponse)
def _probe() -> ProbeResponse:
    """Startup, readiness, and liveness probes: return success only."""
    return ProbeResponse(status="ok")


def run_api_server(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Run the API server with uvicorn."""
    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=False)


__all__ = ["app", "run_api_server"]
