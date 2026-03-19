"""
Pydantic schemas for request/response validation and API contracts.
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Re-use crew models for request and response payloads
from agent.crew import (
    ChatMessage,
    ChatSummaryPayload,
    TitleGenerationRequest as CrewTitleGenerationRequest,
    TitlePayload,
    PreviewGenerationRequest as CrewPreviewGenerationRequest,
    PreviewPayload,
    ContentSummarizationRequest as CrewContentSummarizationRequest,
    ContentSummaryPayload,
)

# ----- Health -----


class HealthResponse(BaseModel):
    """Health check response."""

    service: str = Field(..., description="Service name")
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Health status"
    )
    version: str = Field(..., description="API version")


class ProbeResponse(BaseModel):
    """Kubernetes probe response (startup, liveness, readiness)."""

    status: Literal["ok"] = Field(..., description="Probe status")


# ----- Base Models -----


class BaseAgentRequest(BaseModel):
    """Base request model with common fields for all agent requests"""

    smtip_tid: str = Field(
        ..., description="Simpplr tenant ID for LLM request headers (x-smtip-tid)"
    )
    smtip_feature: str = Field(
        ...,
        description="Simpplr feature identifier for LLM request headers (x-smtip-feature)",
    )
    model: str = Field(..., description="LLM model name to use for the request")
    reasoning_effort: Optional[str] = Field(
        None,
        description="Reasoning effort level for the LLM (low, medium, high). "
        "When set, overrides the server default from master_config.",
    )
    user_id: Optional[str] = Field(None, description="Tracing: user id for Langfuse")
    session_id: Optional[str] = Field(
        None, description="Tracing: session id for Langfuse"
    )
    tags: Optional[list[str]] = Field(None, description="Tracing: tags for Langfuse")

    @field_validator("smtip_tid", "smtip_feature", "model", mode="before")
    @classmethod
    def strip_tenant_fields(cls, v: str) -> str:
        """Strip leading/trailing whitespace to avoid illegal header values."""
        return v.strip() if isinstance(v, str) else v

    @field_validator("reasoning_effort", mode="before")
    @classmethod
    def validate_reasoning_effort(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower() if isinstance(v, str) else v
        if v not in ("low", "medium", "high"):
            raise ValueError("reasoning_effort must be one of: low, medium, high")
        return v


class BaseAgentResponse(BaseModel):
    """Base response model for all agent outputs"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request ID (UUID4)",
    )
    success: bool = Field(..., description="Whether the request was successful")
    error: Optional[str] = Field(None, description="Error message if request failed")
    latency_seconds: Optional[float] = Field(
        None, description="Request latency in seconds"
    )


# ----- Chat Summarisation Models -----


class ChatSummarisationRequest(BaseAgentRequest):
    """Request model for chat summarisation"""

    request_id: str = Field(..., description="Client-generated request ID")
    messages: list[ChatMessage] = Field(
        ..., description="List of chat messages to summarize", min_length=1
    )
    language: str = Field(
        "en",
        description="Output language or locale for the summary (e.g., en, en-GB, fr-CA, hi-IN)",
    )


class ChatSummarisationResponse(BaseAgentResponse):
    """Response model for chat summarisation"""

    content: Optional[ChatSummaryPayload] = Field(
        None, description="Chat summary data"
    )


# ----- Title Generation Models -----


class TitleGenerationRequest(CrewTitleGenerationRequest, BaseAgentRequest):
    """Request model for title generation - combines crew request with base agent fields"""
    pass


class TitleGenerationResponse(BaseAgentResponse):
    """Response model for title generation"""

    content: Optional[TitlePayload] = Field(None, description="Generated title data")


# ----- Preview Generation Models -----


class PreviewGenerationRequest(CrewPreviewGenerationRequest, BaseAgentRequest):
    """Request model for preview generation - combines crew request with base agent fields"""
    pass


class PreviewGenerationResponse(BaseAgentResponse):
    """Response model for preview generation"""

    content: Optional[PreviewPayload] = Field(
        None, description="Generated preview data"
    )


# ----- Content Summarization Models -----


class ContentSummarizationRequest(CrewContentSummarizationRequest, BaseAgentRequest):
    """Request model for content summarization - combines crew request with base agent fields"""
    pass


class ContentSummarizationResponse(BaseAgentResponse):
    """Response model for content summarization"""

    content: Optional[ContentSummaryPayload] = Field(
        None, description="Generated content summary data"
    )


# ----- Error responses (RFC 7807–style) -----


class ErrorDetail(BaseModel):
    """Structured error payload for failed requests."""

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(..., description="Short human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Human-readable explanation")
    code: Optional[str] = Field(None, description="Machine-readable error code")
    trace_id: Optional[str] = Field(None, description="Request/trace id for support")
    timestamp: Optional[str] = Field(None, description="ISO8601 timestamp")
    instance: Optional[str] = Field(None, description="Request path")
