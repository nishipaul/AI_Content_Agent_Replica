"""Crew run event models (run_with_tracing start/end)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import LoggableModel


class CrewRunStartEvent(LoggableModel, BaseModel):
    """Start of a crew run (run_with_tracing)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["crew_run"] = Field(default="crew_run", description="Event name")
    event_phase: Literal["start"] = Field(default="start", description="Event phase")
    operation: str | None = Field(default=None, description="Operation name")
    stream: bool | None = Field(default=None, description="Streaming mode")
    has_prior_context: bool | None = Field(
        default=None, description="Prior context injected"
    )


class CrewRunEndEvent(LoggableModel, BaseModel):
    """End of a crew run (success or failure)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["crew_run"] = Field(default="crew_run", description="Event name")
    event_phase: Literal["end"] = Field(default="end", description="Event phase")
    status: Literal["success", "failure"] = Field(description="Outcome")
    duration_ms: int = Field(ge=0, description="Duration in milliseconds")
    error_type: str | None = Field(
        default=None, description="Exception type when status=failure"
    )
