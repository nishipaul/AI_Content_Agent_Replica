"""Mandatory context bound to every log event. No sensitive fields."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .base import LoggableModel


class LogEventContext(LoggableModel, BaseModel):
    """Mandatory context bound to every log event. No sensitive fields."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(description="Tenant/context ID (e.g. smtip_tid)")
    service_name: str = Field(description="Service/feature name (e.g. smtip_feature)")
    agent_id: str = Field(description="Agent identifier")
    session_id: str = Field(description="Session identifier")
    user_id: str | None = Field(
        default=None, description="User identifier if available"
    )
    component: str | None = Field(
        default=None, description="Component name (e.g. base_crew, redis_connector)"
    )
