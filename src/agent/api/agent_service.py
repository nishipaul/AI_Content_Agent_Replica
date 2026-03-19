"""
Agent service: tenant validation, AI config, and crew execution.

Use this module from routes (and other callers) for all agent-related business logic.
Uses the shared AgentConfigClient connection via tenant.py and the AI config SDK.
Logging follows ai-platform-infra-boilerplate: structlog with event_span (crew_run start/end).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import yaml

from agent.api.constants import (
    DEFAULT_LLM_API,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    ENABLE_OBSERVABILITY,
    ENVIRONMENT,
    LLM_COMPLETIONS_ENDPOINT,
    LLM_CONTEXT_WINDOW_SIZE,
    LLM_GATEWAY_TIMEOUT,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_RESPONSES_ENDPOINT,
    LLM_RETRIES,
    LLM_TEMPERATURE,
    MASTER_CONFIG_PATH,
    REGION,
    SERVICE_ID,
    SERVICE_NAME,
    TRACE_TYPE,
)
from agent.api.schemas import (
    BaseAgentResponse,
    ChatSummarisationResponse,
    TitleGenerationResponse,
    PreviewGenerationResponse,
    ContentSummarizationResponse,
)
from agent.crew import (
    ChatSummariser,  # For chat summarisation
    TitleGenerator,  # For title generation
    PreviewGenerator,  # For preview generation
    ContentSummariser,  # For content summarization
)
from agent.utils.logging_config import CrewRunStartEvent, event_span, get_logger

_agent_runtime_config: dict[str, Any] | None = None


def _load_agent_runtime_config(*, reload: bool = False) -> dict[str, Any]:
    """Load agent_runtime_config from master_config.yaml. Use reload=True to re-read file (for dynamic toggles)."""
    global _agent_runtime_config
    if reload or _agent_runtime_config is None:
        with open(MASTER_CONFIG_PATH, "r") as f:
            master = yaml.safe_load(f)
        _agent_runtime_config = master.get("agent_runtime_config", {})
        if _agent_runtime_config is None:
            _agent_runtime_config = {}
    return _agent_runtime_config


def get_agent_runtime_config(reload: bool = False) -> dict[str, Any]:
    """Return agent runtime config (from master_config.yaml). Use reload=True to re-read file for dynamic endpoint toggles."""
    return _load_agent_runtime_config(reload=reload)


def is_rest_api_enabled(reload_config: bool = True) -> bool:
    config = get_agent_runtime_config(reload=reload_config)
    return bool(config.get("endpoints", {}).get("rest_api_enabled"))


def is_websocket_enabled(reload_config: bool = True) -> bool:
    config = get_agent_runtime_config(reload=reload_config)
    return bool(config.get("endpoints", {}).get("websocket_enabled"))


def is_kafka_enabled(reload_config: bool = True) -> bool:
    config = get_agent_runtime_config(reload=reload_config)
    return bool(config.get("endpoints", {}).get("kafka_enabled"))


async def run_agentic_crew(inputs: dict[str, Any]) -> Any:
    """
    Run the crew with the given inputs.
    Syncs prompts from Langfuse when enabled, then runs the crew with tracing.
    Dynamically selects the crew class based on crew_type.
    """
    agent_runtime_config = _load_agent_runtime_config()
    use_crewai_external_memory = bool(
        agent_runtime_config.get("memory", {}).get("short_term", False)
    )

    reasoning_effort = inputs.get("reasoning_effort", None)
    crew_type = inputs.get("crew_type", "chat_summariser")
    
    # Map crew_type to crew class
    crew_class_map = {
        "chat_summariser": ChatSummariser,
        "title_generator": TitleGenerator,
        "preview_generator": PreviewGenerator,
        "content_summariser": ContentSummariser,
    }
    
    crew_class = crew_class_map.get(crew_type)
    if not crew_class:
        raise ValueError(f"Unknown crew_type: {crew_type}")
    
    # Instantiate the crew
    crew = crew_class(
        smtip_tid=inputs.get("smtip_tid", ""),
        smtip_feature=inputs.get("smtip_feature", ""),
        model=inputs.get("model", ""),
        user_id=inputs.get("user_id", ""),
        session_id=inputs.get("session_id", ""),
        service_id=SERVICE_ID,
        service_name=SERVICE_NAME,
        agent_id=SERVICE_ID,
        api=DEFAULT_LLM_API,
        completions_endpoint=LLM_COMPLETIONS_ENDPOINT,
        responses_endpoint=LLM_RESPONSES_ENDPOINT,
        temperature=inputs.get("temperature", LLM_TEMPERATURE),
        max_output_tokens=inputs.get("max_output_tokens", LLM_MAX_OUTPUT_TOKENS),
        reasoning_effort=reasoning_effort,
        instructions=inputs.get("instructions", None),
        trace_name=f"{SERVICE_ID}-{ENVIRONMENT}",
        enable_observability=ENABLE_OBSERVABILITY,
        use_crewai_external_memory=use_crewai_external_memory,
        llm_gateway_timeout=LLM_GATEWAY_TIMEOUT,
        context_window_size=inputs.get("context_window_size", LLM_CONTEXT_WINDOW_SIZE),
        retries=LLM_RETRIES,
    )
    
    # Build tags
    all_tags = [
        inputs.get("smtip_tid", ""),
        inputs.get("smtip_feature", ""),
        SERVICE_NAME,
        SERVICE_ID,
        REGION,
        TRACE_TYPE,
    ] + inputs.get("tags", [])
    
    # Run the crew
    return crew.run_with_tracing(
        inputs=inputs, tags=all_tags, metadata=inputs.get("metadata")
    )


def build_agent_inputs(
    smtip_tid: str = "",
    smtip_feature: str = "",
    model: str = DEFAULT_MODEL,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build the inputs dict expected by run_agentic_crew from request fields.

    Constant fields (smtip_tid, smtip_feature, model, user_id, session_id, tags)
    are always present with sensible defaults.  Any crew-specific keyword
    arguments are merged into the result via **kwargs.
    """
    inputs: dict[str, Any] = {
        "smtip_tid": smtip_tid,
        "smtip_feature": smtip_feature,
        "model": model or DEFAULT_MODEL,
        "user_id": user_id or "",
        "session_id": session_id or "",
        "tags": tags or [],
        "metadata": metadata or {},
    }
    if reasoning_effort:
        inputs["reasoning_effort"] = reasoning_effort
    for key, value in kwargs.items():
        if isinstance(value, dict):
            inputs[key] = json.dumps(value) if key.endswith("_data") else value
        elif isinstance(value, list):
            # Convert list of Pydantic models to list of dicts, then to JSON string
            if value and hasattr(value[0], "model_dump"):
                inputs[key] = json.dumps([item.model_dump() for item in value])
            else:
                inputs[key] = value
        else:
            inputs[key] = value
    return inputs


async def generate_response(
    crew_type: str,
    smtip_tid: str | None = None,
    smtip_feature: str | None = None,
    model: str = DEFAULT_MODEL,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
    **kwargs: Any,
) -> BaseAgentResponse:
    """
    Unified dynamic function to run any crew and return the appropriate response.
    Dynamically selects the response class based on crew_type.
    """
    # Map crew_type to response class
    response_class_map = {
        "chat_summariser": ChatSummarisationResponse,
        "title_generator": TitleGenerationResponse,
        "preview_generator": PreviewGenerationResponse,
        "content_summariser": ContentSummarizationResponse,
    }
    
    response_class = response_class_map.get(crew_type)
    if not response_class:
        raise ValueError(f"Unknown crew_type: {crew_type}")
    
    inputs = build_agent_inputs(
        smtip_tid=smtip_tid or "",
        smtip_feature=smtip_feature or "",
        model=model,
        user_id=user_id,
        session_id=session_id or str(uuid.uuid4()),
        tags=tags or [],
        metadata=metadata or {},
        reasoning_effort=reasoning_effort,
        crew_type=crew_type,
        **kwargs,
    )
    
    tenant_id = smtip_tid or "-"
    service_name = smtip_feature or "-"
    agent_id = SERVICE_ID
    session_id_val = session_id or str(uuid.uuid4())
    log = get_logger(
        "agent_service",
        tenant_id=tenant_id,
        service_name=service_name,
        agent_id=agent_id,
        session_id=session_id_val,
        user_id=user_id,
        component="agent_service",
    )
    start_payload = CrewRunStartEvent(
        tenant_id=tenant_id,
        service_name=service_name,
        agent_id=agent_id,
        session_id=session_id_val,
        operation=f"Crew Run for {SERVICE_ID}",
        stream=False,
    )
    start = time.time()
    
    try:
        with event_span(log, start_payload, input_data=inputs):
            result_value = await run_agentic_crew(inputs)
        latency_seconds = round(time.time() - start, 3)
        content = result_value
        if (
            result_value is not None
            and hasattr(result_value, "pydantic")
            and result_value.pydantic is not None
        ):
            content = result_value.pydantic
        elif result_value is not None and hasattr(result_value, "raw"):
            content = result_value.raw
        return response_class(
            id=str(uuid.uuid4()),
            success=True,
            content=content,
            error=None,
            latency_seconds=latency_seconds,
        )
    except Exception as e:
        latency_seconds = round(time.time() - start, 3)
        return response_class(
            id=str(uuid.uuid4()),
            success=False,
            content=None,
            error=str(e),
            latency_seconds=latency_seconds,
        )
