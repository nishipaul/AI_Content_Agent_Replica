"""
Agent framework: re-exports from ai_infra_python_sdk_core.base_crew for backward compatibility.

Prefer: from ai_infra_python_sdk_core.base_crew import BaseAICrew
"""

from ai_infra_python_sdk_core.base_crew import (
    BaseAICrew,  # type: ignore[import-untyped]
)

__all__ = ["BaseAICrew"]
