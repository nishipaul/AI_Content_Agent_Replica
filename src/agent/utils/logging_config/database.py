"""Database/connection event models (e.g. Redis connect/close start/end)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import LoggableModel


class DatabaseStartEvent(LoggableModel, BaseModel):
    """Start of a database/connection operation (e.g. Redis connect or close)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: str = Field(description="Event name (e.g. redis_connect, redis_close)")
    event_phase: Literal["start"] = Field(default="start", description="Event phase")
    operation: Literal["connect", "close"] = Field(description="Operation type")


class DatabaseEndEvent(LoggableModel, BaseModel):
    """End of a database/connection operation (e.g. Redis connect or close)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: str = Field(description="Event name (e.g. redis_connect, redis_close)")
    event_phase: Literal["end"] = Field(default="end", description="Event phase")
    status: Literal["success", "failure"] = Field(description="Outcome")
    duration_ms: int = Field(ge=0, description="Duration in milliseconds")
    error_type: str | None = Field(
        default=None, description="Exception type when status=failure"
    )
    operation: Literal["connect", "close"] | None = Field(
        default=None, description="Operation type"
    )
    mode: Literal["standalone", "cluster"] | None = Field(
        default=None, description="Redis mode"
    )
    node_count: int | None = Field(
        default=None, description="Cluster node count when mode=cluster"
    )
