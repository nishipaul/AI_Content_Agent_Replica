"""Event payload unions, ErrorEvent, and end-payload builder for start events."""

from __future__ import annotations

from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from .base import LoggableModel
from .crew_run import CrewRunEndEvent, CrewRunStartEvent
from .database import DatabaseEndEvent, DatabaseStartEvent
from .memory import (
    MemoryLoadEndEvent,
    MemoryLoadStartEvent,
    MemorySaveEndEvent,
    MemorySaveStartEvent,
    MemorySearchEndEvent,
    MemorySearchStartEvent,
)


class ErrorEvent(LoggableModel, BaseModel):
    """
    Error event for log_error().
    At DEBUG: message, error_type, and traceback are logged.
    At INFO: message and error_type only (no traceback).
    At WARNING/ERROR: only message (and optionally error_type) are logged.
    """

    model_config = ConfigDict(extra="forbid")

    event: str = Field(default="error", description="Event name")
    message: str = Field(description="Error message")
    error_type: str | None = Field(default=None, description="Exception type name")
    traceback: str | None = Field(
        default=None, description="Full traceback (logged only at DEBUG)"
    )


StartEventPayload = Union[
    CrewRunStartEvent,
    DatabaseStartEvent,
    MemoryLoadStartEvent,
    MemorySaveStartEvent,
    MemorySearchStartEvent,
]

EndEventPayload = Union[
    CrewRunEndEvent,
    DatabaseEndEvent,
    MemoryLoadEndEvent,
    MemorySaveEndEvent,
    MemorySearchEndEvent,
]


def _mandatory_from_start(start_payload: StartEventPayload) -> dict[str, str]:
    """Extract mandatory context (tenant_id, service_name, agent_id, session_id) from a start event."""
    return {
        "tenant_id": start_payload.tenant_id,
        "service_name": start_payload.service_name,
        "agent_id": start_payload.agent_id,
        "session_id": start_payload.session_id,
    }


def make_end_payload(
    start_payload: StartEventPayload,
    status: str,
    duration_ms: int,
    error_type: str | None,
) -> EndEventPayload:
    """Build the matching end event from a start event payload."""
    base = {
        "tenant_id": start_payload.tenant_id,
        "service_name": start_payload.service_name,
        "agent_id": start_payload.agent_id,
        "session_id": start_payload.session_id,
        "status": status,
        "duration_ms": duration_ms,
        "error_type": error_type,
    }
    if isinstance(start_payload, CrewRunStartEvent):
        return CrewRunEndEvent(**base)
    if isinstance(start_payload, DatabaseStartEvent):
        return DatabaseEndEvent(
            **base,
            event=start_payload.event,
            operation=start_payload.operation,
        )
    if isinstance(start_payload, MemoryLoadStartEvent):
        return MemoryLoadEndEvent(**base)
    if isinstance(start_payload, MemorySaveStartEvent):
        return MemorySaveEndEvent(**base)
    if isinstance(start_payload, MemorySearchStartEvent):
        return MemorySearchEndEvent(**base)
    raise TypeError(f"Unknown start event type: {type(start_payload)}")
