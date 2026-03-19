"""
Structured logging aligned with ai-platform-infra-boilerplate.

Uses structlog from ai_infra (JSON logs, event-driven start/end, context, redaction).
Datamodels mirror the base package: LoggableModel, LogEventContext, CrewRun*,
Database*, Memory*, ErrorEvent, StartEventPayload, EndEventPayload, constants.
Configure once at startup via configure_logging(). Use get_logger() with request
context for request-scoped logs; use get_logger_without_crew_context(component=...)
for components without crew context.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ai_infra_python_sdk_core.ai_infra.logging_config import (
    configure_structlog,
    get_effective_log_level,
)
from ai_infra_python_sdk_core.ai_infra.logging_config import (
    get_logger as get_structlog_logger,
)
from ai_infra_python_sdk_core.ai_infra.logging_config import (
    get_logger_without_crew_context as get_structlog_logger_without_context,
)
from ai_infra_python_sdk_core.ai_infra.logging_config import (
    log_at_level,
    log_error,
    log_event_end,
    log_event_start,
)

from .base import LoggableModel
from .config import event_span
from .constants import (
    DEFAULT_LOG_LEVEL,
    EVENT_PHASE_END,
    EVENT_PHASE_START,
    LOG_LEVEL_ENV_VAR,
    LOG_SENTINEL_UNSET,
    STATUS_FAILURE,
    STATUS_SUCCESS,
    VALID_LOG_LEVELS,
)
from .context import LogEventContext
from .crew_run import CrewRunEndEvent, CrewRunStartEvent
from .database import DatabaseEndEvent, DatabaseStartEvent
from .events import EndEventPayload, ErrorEvent, StartEventPayload, make_end_payload
from .memory import (
    MemoryLoadEndEvent,
    MemoryLoadStartEvent,
    MemorySaveEndEvent,
    MemorySaveStartEvent,
    MemorySearchEndEvent,
    MemorySearchStartEvent,
)

__all__ = [
    # Config / API
    "configure_logging",
    "get_logger",
    "get_logger_without_crew_context",
    "get_structlog_logger",
    "get_structlog_logger_without_context",
    "event_span",
    "log_event_start",
    "log_event_end",
    "log_error",
    "log_at_level",
    "get_effective_log_level",
    "make_end_payload",
    # Constants
    "DEFAULT_LOG_LEVEL",
    "LOG_LEVEL_ENV_VAR",
    "VALID_LOG_LEVELS",
    "EVENT_PHASE_START",
    "EVENT_PHASE_END",
    "STATUS_SUCCESS",
    "STATUS_FAILURE",
    "LOG_SENTINEL_UNSET",
    # Base / context
    "LoggableModel",
    "LogEventContext",
    # Crew run
    "CrewRunStartEvent",
    "CrewRunEndEvent",
    # Database
    "DatabaseStartEvent",
    "DatabaseEndEvent",
    # Memory
    "MemoryLoadStartEvent",
    "MemoryLoadEndEvent",
    "MemorySaveStartEvent",
    "MemorySaveEndEvent",
    "MemorySearchStartEvent",
    "MemorySearchEndEvent",
    # Events
    "ErrorEvent",
    "StartEventPayload",
    "EndEventPayload",
]

APP_LOGGER_NAME = "agent"


def _resolve_log_level(level: str | None = None) -> str:
    """
    Resolve log level: explicit level > AI_INFRA_LOG_LEVEL env > LOG_LEVEL env > default.
    Returns a valid level (DEBUG, INFO, WARNING, ERROR) or DEFAULT_LOG_LEVEL.
    """
    if level is not None and str(level).strip():
        raw = str(level).strip().upper()
        if raw in VALID_LOG_LEVELS:
            return raw
    env_level = os.environ.get(LOG_LEVEL_ENV_VAR, "").strip().upper()
    if env_level in VALID_LOG_LEVELS:
        return env_level
    log_level = os.environ.get("LOG_LEVEL", "").strip().upper()
    if log_level in VALID_LOG_LEVELS:
        return log_level
    return DEFAULT_LOG_LEVEL


def configure_logging(
    level: str | None = None,
    json_logs: bool = True,
) -> None:
    """
    Configure structlog for the application (boilerplate strategy).

    Call once at startup. Log level (in order): explicit `level` argument,
    then AI_INFRA_LOG_LEVEL env var, then LOG_LEVEL env var, then default INFO.
    Also quiets uvicorn/httpx.
    """
    resolved = _resolve_log_level(level)
    configure_structlog(json_logs=json_logs, log_level=resolved)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(
    name: str,
    *,
    tenant_id: str | None = None,
    service_name: str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    component: str | None = None,
    **extra: Any,
):
    """
    Return a structlog logger.

    - With context (tenant_id, service_name, agent_id, session_id): use for
      request-scoped logs. Pass component=name for the module.
    - Without context: omit the context args (or pass None); returns a logger
      with component=name and placeholder context (get_logger_without_crew_context).
    """
    if (
        tenant_id is not None
        and service_name is not None
        and agent_id is not None
        and session_id is not None
    ):
        return get_structlog_logger(
            tenant_id=tenant_id,
            service_name=service_name,
            agent_id=agent_id,
            session_id=session_id,
            user_id=user_id,
            component=component or name,
            **extra,
        )
    return get_logger_without_crew_context(component or name, **extra)


def get_logger_without_crew_context(component: str, **extra: Any):
    """Return a structlog logger for components without crew/request context."""
    return get_structlog_logger_without_context(component=component, **extra)
