"""Memory event models: load, save, and search (CrewAI external memory) start/end."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import LoggableModel

# --- Memory load (prior context inject) ---


class MemoryLoadStartEvent(LoggableModel, BaseModel):
    """Start of loading prior context from memory."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["memory_load"] = Field(
        default="memory_load", description="Event name"
    )
    event_phase: Literal["start"] = Field(default="start", description="Event phase")
    operation: str | None = Field(default=None, description="Operation name")


class MemoryLoadEndEvent(LoggableModel, BaseModel):
    """End of loading prior context from memory."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["memory_load"] = Field(
        default="memory_load", description="Event name"
    )
    event_phase: Literal["end"] = Field(default="end", description="Event phase")
    status: Literal["success", "failure"] = Field(description="Outcome")
    duration_ms: int = Field(ge=0, description="Duration in milliseconds")
    entry_count: int | None = Field(
        default=None, description="Number of entries loaded"
    )
    error_type: str | None = Field(
        default=None, description="Exception type when status=failure"
    )


# --- Memory save ---


class MemorySaveStartEvent(LoggableModel, BaseModel):
    """Start of saving a memory entry (CrewAI external memory)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["memory_save"] = Field(
        default="memory_save", description="Event name"
    )
    event_phase: Literal["start"] = Field(default="start", description="Event phase")
    operation: str | None = Field(default=None, description="Operation name")


class MemorySaveEndEvent(LoggableModel, BaseModel):
    """End of saving a memory entry."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["memory_save"] = Field(
        default="memory_save", description="Event name"
    )
    event_phase: Literal["end"] = Field(default="end", description="Event phase")
    status: Literal["success", "failure"] = Field(description="Outcome")
    duration_ms: int = Field(ge=0, description="Duration in milliseconds")
    entry_count: int | None = Field(default=None, description="Entries after save")
    error_type: str | None = Field(
        default=None, description="Exception type when status=failure"
    )


# --- Memory search ---


class MemorySearchStartEvent(LoggableModel, BaseModel):
    """Start of searching memory (CrewAI external memory)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["memory_search"] = Field(
        default="memory_search", description="Event name"
    )
    event_phase: Literal["start"] = Field(default="start", description="Event phase")
    operation: str | None = Field(default=None, description="Operation name")


class MemorySearchEndEvent(LoggableModel, BaseModel):
    """End of searching memory."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="-", description="Tenant/context ID (mandatory)")
    service_name: str = Field(
        default="-", description="Service/feature name (mandatory)"
    )
    agent_id: str = Field(default="-", description="Agent identifier (mandatory)")
    session_id: str = Field(default="-", description="Session identifier (mandatory)")
    event: Literal["memory_search"] = Field(
        default="memory_search", description="Event name"
    )
    event_phase: Literal["end"] = Field(default="end", description="Event phase")
    status: Literal["success", "failure"] = Field(description="Outcome")
    duration_ms: int = Field(ge=0, description="Duration in milliseconds")
    entry_count: int | None = Field(
        default=None, description="Number of entries returned"
    )
    error_type: str | None = Field(
        default=None, description="Exception type when status=failure"
    )
