"""
Tool input schema tests: validate Pydantic models and tool structure.
No actual tool execution or external APIs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.tools.custom_tool import MyCustomTool, MyCustomToolInput


@pytest.mark.unit
def test_my_custom_tool_input_valid() -> None:
    """MyCustomToolInput accepts argument string."""
    inp = MyCustomToolInput(argument="test value")
    assert inp.argument == "test value"


@pytest.mark.unit
def test_my_custom_tool_input_missing_raises() -> None:
    """MyCustomToolInput raises ValidationError when argument missing."""
    with pytest.raises(ValidationError):
        MyCustomToolInput()


@pytest.mark.unit
def test_my_custom_tool_has_schema_and_run() -> None:
    """MyCustomTool has name, description, args_schema, and _run method."""
    tool = MyCustomTool()
    assert tool.name
    assert tool.description
    assert tool.args_schema is MyCustomToolInput
    result = tool._run(argument="hello")
    assert isinstance(result, str)
    assert "example" in result.lower() or "output" in result.lower()
