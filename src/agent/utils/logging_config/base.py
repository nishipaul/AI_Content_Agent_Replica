"""Abstract base for logging models: export non-null, non-sentinel dict for JSON logging."""

from __future__ import annotations

from abc import ABC
from typing import Any

from .constants import LOG_SENTINEL_UNSET


class LoggableModel(ABC):
    """Base for context and event models. Provides to_log_dict() for JSON logging."""

    def to_log_dict(self) -> dict[str, Any]:
        """Export JSON-suitable dict of non-null values only (no sentinel '-')."""
        d = self.model_dump(exclude_none=True)  # type: ignore[attr-defined]
        return {k: v for k, v in d.items() if v is not None and v != LOG_SENTINEL_UNSET}
