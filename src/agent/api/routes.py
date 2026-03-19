"""
REST, WebSocket, and Streaming routes for the CrewAI API.

Only endpoint definitions; business logic lives in agent_service.
"""

from __future__ import annotations

from typing import Union

from openinference.instrumentation.crewai import (
    CrewAIInstrumentor,  # Should always be at the start
)

CrewAIInstrumentor().instrument(skip_dep_check=True)


import json
import os

import yaml
from ai_infra_python_sdk_core.ai_infra.observability.pipeline import (
    trace_ai_config,
    trace_prompt_sync,
    trace_ws_lifecycle,
    tracing_agents,
)
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status

from agent.api.agent_service import (
    generate_response,
    get_agent_runtime_config,
    is_rest_api_enabled,
)
from agent.api.agent_service import is_websocket_enabled as is_websocket_enabled_runtime
from agent.api.constants import (
    _COMMON_SERVICE_KWARGS,
    AGENTS_CONFIG_PATH,
    APPLICATION_NAME,
    PROMPT_CONFIG_PATH,
    ROUTER_PREFIX,
    SERVICE_ID,
    SERVICE_NAME,
    TASKS_CONFIG_PATH,
    agent_prompt_config,
    agent_runtime_config,
)
from agent.api.schemas import (
    ChatSummarisationRequest,
    ChatSummarisationResponse,
    TitleGenerationRequest,
    TitleGenerationResponse,
    PreviewGenerationRequest,
    PreviewGenerationResponse,
    ContentSummarizationRequest,
    ContentSummarizationResponse,
    HealthResponse,
    ProbeResponse,
)
from agent.api.tenant import TenantConfigUnavailableError, tenant_exists
from agent.utils.logging_config import get_logger, get_logger_without_crew_context

load_dotenv()


# For endpoints without request context (health, probes)
logger = get_logger_without_crew_context("api")


config = get_agent_runtime_config()
router = APIRouter(prefix=ROUTER_PREFIX, tags=["v1"])

websocket_route_enabled = bool(
    config.get("endpoints", {}).get("websocket_enabled", False)
)


def require_rest_api_enabled() -> None:
    """Dependency: raise 404 if REST survey summary endpoint is disabled (checks config on each request)."""
    if not is_rest_api_enabled(reload_config=True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This endpoint is currently disabled",
        )


def require_websocket_enabled() -> None:
    """Dependency: raise 404 if WebSocket survey summary endpoint is disabled (checks config on each request)."""
    if not is_websocket_enabled_runtime(reload_config=True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This endpoint is currently disabled",
        )


async def require_tenant_exists(
    request: Union[ChatSummarisationRequest, TitleGenerationRequest, PreviewGenerationRequest]
) -> Union[ChatSummarisationRequest, TitleGenerationRequest, PreviewGenerationRequest]:
    """Dependency: raise 403 if tenant is not registered or agent not enabled. Returns the request for the route.
    
    Works dynamically with all crew request types (ChatSummarisationRequest, TitleGenerationRequest, PreviewGenerationRequest).
    """
    try:
        if not await tenant_exists(request.smtip_tid, request.smtip_feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant not registered or agent not enabled for this tenant/feature",
            )
    except TenantConfigUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message,
        ) from e
    return request


# ----- Health -----


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check for load balancers and readiness probes."""
    logger.debug("health_check_requested")
    return HealthResponse(
        service=SERVICE_NAME,
        status="healthy",
        version="1.0.0",
    )


@router.get("/startup", response_model=ProbeResponse)
async def startup_probe() -> ProbeResponse:
    """Startup probe: indicates the application has started."""
    return ProbeResponse(status="ok")


@router.get("/live", response_model=ProbeResponse)
async def liveness_probe() -> ProbeResponse:
    """Liveness probe: indicates the application is alive."""
    return ProbeResponse(status="ok")


@router.get("/ready", response_model=ProbeResponse)
async def readiness_probe() -> ProbeResponse:
    """Readiness probe: indicates the application is ready to receive traffic."""
    return ProbeResponse(status="ok")


# ----- REST API -----


@router.post(
    "/chat-summarise",  # Change the endpoint path here as per your use case
    response_model=ChatSummarisationResponse,
    status_code=200,
    summary=f"Generate {SERVICE_NAME}",
    dependencies=[Depends(require_rest_api_enabled)],
    responses={
        200: {"description": "Success"},
        403: {"description": "Tenant not registered or agent not enabled"},
        404: {"description": "Endpoint disabled"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)
# Mandatory decorators for tracing
@tracing_agents(
    application_name=APPLICATION_NAME,
    common_service_kwargs=_COMMON_SERVICE_KWARGS,
)
@trace_ai_config()
@trace_prompt_sync(
    agent_runtime_config=agent_runtime_config,
    agent_prompt_config=agent_prompt_config,
    agents_config_path=AGENTS_CONFIG_PATH,
    tasks_config_path=TASKS_CONFIG_PATH,
    prompt_config_path=PROMPT_CONFIG_PATH,
)
async def process_chat_summarisation_request(request: ChatSummarisationRequest) -> ChatSummarisationResponse:
    """Generate a response from the agent."""
    # Get ctx from the request (attached by @with_tracing decorator)
    ctx = getattr(request, "_pipeline_ctx")

    # Note: Tenant validation is already done by @with_ai_config decorator which fetches AI config and raises 403 if not found

    log = get_logger(
        "api",
        tenant_id=request.smtip_tid or "-",
        service_name=request.smtip_feature or "-",
        agent_id=SERVICE_ID,
        session_id=request.session_id or "-",
        component="api",
    )
    log.info(
        f"{SERVICE_NAME} request",
        smtip_tid=request.smtip_tid,
        smtip_feature=request.smtip_feature,
    )
    try:
        crew_specific_fields = {
            k: v
            for k, v in request.model_dump().items()
            if k
            not in {
                "smtip_tid",
                "smtip_feature",
                "model",
                "user_id",
                "session_id",
                "tags",
                "trace_id",
                "metadata",
                "reasoning_effort",
            }
        }
        response = await generate_response(
            crew_type="chat_summariser",
            smtip_tid=request.smtip_tid,
            smtip_feature=request.smtip_feature,
            model=request.model or "auto-route",
            user_id=request.user_id,
            session_id=ctx.session_id,
            tags=ctx.all_tags,
            trace_id=ctx.trace_id,
            metadata=ctx.metadata,
            reasoning_effort=request.reasoning_effort or None,
            **crew_specific_fields,
        )
        if not response.success:
            log.error(f"{SERVICE_NAME} request failed", error=response.error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Agent failed",
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"{SERVICE_NAME} request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e





@router.post(
    "/generate-title",  # Change the endpoint path here as per your use case
    response_model=TitleGenerationResponse,
    status_code=200,
    summary=f"Generate {SERVICE_NAME}",
    dependencies=[Depends(require_rest_api_enabled)],
    responses={
        200: {"description": "Success"},
        403: {"description": "Tenant not registered or agent not enabled"},
        404: {"description": "Endpoint disabled"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)
# Mandatory decorators for tracing
@tracing_agents(
    application_name=APPLICATION_NAME,
    common_service_kwargs=_COMMON_SERVICE_KWARGS,
)
@trace_ai_config()
@trace_prompt_sync(
    agent_runtime_config=agent_runtime_config,
    agent_prompt_config=agent_prompt_config,
    agents_config_path=AGENTS_CONFIG_PATH,
    tasks_config_path=TASKS_CONFIG_PATH,
    prompt_config_path=PROMPT_CONFIG_PATH,
)
async def process_title_generation_request(request: TitleGenerationRequest) -> TitleGenerationResponse:
    """Generate a response from the agent."""
    # Get ctx from the request (attached by @with_tracing decorator)
    ctx = getattr(request, "_pipeline_ctx")

    # Note: Tenant validation is already done by @with_ai_config decorator which fetches AI config and raises 403 if not found

    log = get_logger(
        "api",
        tenant_id=request.smtip_tid or "-",
        service_name=request.smtip_feature or "-",
        agent_id=SERVICE_ID,
        session_id=request.session_id or "-",
        component="api",
    )
    log.info(
        f"{SERVICE_NAME} request",
        smtip_tid=request.smtip_tid,
        smtip_feature=request.smtip_feature,
    )
    try:
        crew_specific_fields = {
            k: v
            for k, v in request.model_dump().items()
            if k
            not in {
                "smtip_tid",
                "smtip_feature",
                "model",
                "user_id",
                "session_id",
                "tags",
                "trace_id",
                "metadata",
                "reasoning_effort",
            }
        }
        response = await generate_response(
            crew_type="title_generator",
            smtip_tid=request.smtip_tid,
            smtip_feature=request.smtip_feature,
            model=request.model or "auto-route",
            user_id=request.user_id,
            session_id=ctx.session_id,
            tags=ctx.all_tags,
            trace_id=ctx.trace_id,
            metadata=ctx.metadata,
            reasoning_effort=request.reasoning_effort or None,
            **crew_specific_fields,
        )
        if not response.success:
            log.error(f"{SERVICE_NAME} request failed", error=response.error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Agent failed",
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"{SERVICE_NAME} request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e




@router.post(
    "/generate-preview",  # Change the endpoint path here as per your use case
    response_model=PreviewGenerationResponse,
    status_code=200,
    summary=f"Generate {SERVICE_NAME}",
    dependencies=[Depends(require_rest_api_enabled)],
    responses={
        200: {"description": "Success"},
        403: {"description": "Tenant not registered or agent not enabled"},
        404: {"description": "Endpoint disabled"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)
# Mandatory decorators for tracing
@tracing_agents(
    application_name=APPLICATION_NAME,
    common_service_kwargs=_COMMON_SERVICE_KWARGS,
)
@trace_ai_config()
@trace_prompt_sync(
    agent_runtime_config=agent_runtime_config,
    agent_prompt_config=agent_prompt_config,
    agents_config_path=AGENTS_CONFIG_PATH,
    tasks_config_path=TASKS_CONFIG_PATH,
    prompt_config_path=PROMPT_CONFIG_PATH,
)
async def process_preview_generation_request(request: PreviewGenerationRequest) -> PreviewGenerationResponse:
    """Generate a response from the agent."""
    # Get ctx from the request (attached by @with_tracing decorator)
    ctx = getattr(request, "_pipeline_ctx")

    # Note: Tenant validation is already done by @with_ai_config decorator which fetches AI config and raises 403 if not found

    log = get_logger(
        "api",
        tenant_id=request.smtip_tid or "-",
        service_name=request.smtip_feature or "-",
        agent_id=SERVICE_ID,
        session_id=request.session_id or "-",
        component="api",
    )
    log.info(
        f"{SERVICE_NAME} request",
        smtip_tid=request.smtip_tid,
        smtip_feature=request.smtip_feature,
    )
    try:
        crew_specific_fields = {
            k: v
            for k, v in request.model_dump().items()
            if k
            not in {
                "smtip_tid",
                "smtip_feature",
                "model",
                "user_id",
                "session_id",
                "tags",
                "trace_id",
                "metadata",
                "reasoning_effort",
            }
        }
        response = await generate_response(
            crew_type="preview_generator",
            smtip_tid=request.smtip_tid,
            smtip_feature=request.smtip_feature,
            model=request.model or "auto-route",
            user_id=request.user_id,
            session_id=ctx.session_id,
            tags=ctx.all_tags,
            trace_id=ctx.trace_id,
            metadata=ctx.metadata,
            reasoning_effort=request.reasoning_effort or None,
            **crew_specific_fields,
        )
        if not response.success:
            log.error(f"{SERVICE_NAME} request failed", error=response.error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Agent failed",
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"{SERVICE_NAME} request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e




@router.post(
    "/summarize-content",
    response_model=ContentSummarizationResponse,
    status_code=200,
    summary=f"Summarize Content {SERVICE_NAME}",
    dependencies=[Depends(require_rest_api_enabled)],
    responses={
        200: {"description": "Success"},
        403: {"description": "Tenant not registered or agent not enabled"},
        404: {"description": "Endpoint disabled"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)
@tracing_agents(
    application_name=APPLICATION_NAME,
    common_service_kwargs=_COMMON_SERVICE_KWARGS,
)
@trace_ai_config()
@trace_prompt_sync(
    agent_runtime_config=agent_runtime_config,
    agent_prompt_config=agent_prompt_config,
    agents_config_path=AGENTS_CONFIG_PATH,
    tasks_config_path=TASKS_CONFIG_PATH,
    prompt_config_path=PROMPT_CONFIG_PATH,
)
async def process_content_summarization_request(
    request: ContentSummarizationRequest,
) -> ContentSummarizationResponse:
    """Generate a content summary from the agent."""
    ctx = getattr(request, "_pipeline_ctx")

    log = get_logger(
        "api",
        tenant_id=request.smtip_tid or "-",
        service_name=request.smtip_feature or "-",
        agent_id=SERVICE_ID,
        session_id=request.session_id or "-",
        component="api",
    )
    log.info(
        f"{SERVICE_NAME} content summarization request",
        smtip_tid=request.smtip_tid,
        smtip_feature=request.smtip_feature,
        mode=request.mode,
    )
    try:
        crew_specific_fields = {
            k: v
            for k, v in request.model_dump().items()
            if k
            not in {
                "smtip_tid",
                "smtip_feature",
                "model",
                "user_id",
                "session_id",
                "tags",
                "trace_id",
                "metadata",
                "reasoning_effort",
            }
        }
        response = await generate_response(
            crew_type="content_summariser",
            smtip_tid=request.smtip_tid,
            smtip_feature=request.smtip_feature,
            model=request.model or "auto-route",
            user_id=request.user_id,
            session_id=ctx.session_id,
            tags=ctx.all_tags,
            trace_id=ctx.trace_id,
            metadata=ctx.metadata,
            reasoning_effort=request.reasoning_effort or None,
            **crew_specific_fields,
        )
        if not response.success:
            log.error(f"{SERVICE_NAME} request failed", error=response.error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Agent failed",
            )
        return response
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"{SERVICE_NAME} request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
