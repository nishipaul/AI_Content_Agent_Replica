"""
Structlog configuration and event_span using local datamodels.

Delegates to SDK for configure_structlog, get_logger, log_event_*; provides
event_span that uses local make_end_payload so local CrewRunStartEvent etc. work.
"""

from __future__ import annotations

import time
import traceback
from contextlib import contextmanager
from typing import Any, Generator

from ai_infra_python_sdk_core.ai_infra.logging_config import log_error as sdk_log_error
from ai_infra_python_sdk_core.ai_infra.logging_config import (
    log_event_end as sdk_log_event_end,
)
from ai_infra_python_sdk_core.ai_infra.logging_config import (
    log_event_start as sdk_log_event_start,
)

from .constants import STATUS_FAILURE, STATUS_SUCCESS
from .events import StartEventPayload, make_end_payload


@contextmanager
def event_span(
    log: Any,
    start_payload: StartEventPayload,
    *,
    input_data: dict[str, Any] | None = None,
) -> Generator[None, None, None]:
    """
    Context manager: log start on enter, end with status and duration_ms on exit.
    Uses local datamodels and make_end_payload so local CrewRunStartEvent is supported.
    """
    sdk_log_event_start(log, start_payload, input_data=input_data)
    start = time.monotonic()
    error_type: str | None = None
    try:
        yield
    except Exception as e:
        error_type = type(e).__name__
        sdk_log_error(
            log,
            str(e),
            error_type=error_type,
            traceback_str=traceback.format_exc(),
        )
        raise
    finally:
        duration_ms = round((time.monotonic() - start) * 1000)
        status = STATUS_FAILURE if error_type is not None else STATUS_SUCCESS
        end_payload = make_end_payload(start_payload, status, duration_ms, error_type)
        sdk_log_event_end(log, end_payload)
