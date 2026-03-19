"""
Main entry point tests: run_hooks() with mocks.
No real crew execution or pre-commit subprocess.
Importing agent.main requires master_config to be loadable; we mock it for run_hooks tests.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def _mock_master_config() -> dict:
    """Fake master_config so agent.main module-level code does not KeyError."""
    return {
        "agent_runtime_config": {},
        "Agent_registry_config": {"id": "test-agent-id"},
    }


@pytest.mark.unit
def test_run_hooks_exits_zero_when_precommit_succeeds() -> None:
    """run_hooks calls pre-commit and exits with its return code (0 when success)."""
    from unittest.mock import mock_open

    with patch("builtins.open", mock_open(read_data="{}")):
        with patch("yaml.safe_load", return_value=_mock_master_config()):
            with patch("subprocess.run", return_value=MagicMock(returncode=0)):
                with pytest.raises(SystemExit) as exc_info:
                    with patch.object(sys, "argv", ["run_hooks"]):
                        from agent.main import run_hooks

                        run_hooks()
                assert exc_info.value.code == 0


@pytest.mark.unit
def test_run_hooks_exits_nonzero_when_precommit_fails() -> None:
    """run_hooks exits with non-zero when pre-commit returns failure."""
    from unittest.mock import mock_open

    with patch("builtins.open", mock_open(read_data="{}")):
        with patch("yaml.safe_load", return_value=_mock_master_config()):
            with patch("subprocess.run", return_value=MagicMock(returncode=1)):
                with pytest.raises(SystemExit) as exc_info:
                    with patch.object(sys, "argv", ["run_hooks"]):
                        from agent.main import run_hooks

                        run_hooks()
                assert exc_info.value.code == 1


@pytest.mark.unit
def test_run_hooks_exits_one_when_precommit_not_found() -> None:
    """run_hooks exits 1 when pre-commit not found."""
    from unittest.mock import mock_open

    with patch("builtins.open", mock_open(read_data="{}")):
        with patch("yaml.safe_load", return_value=_mock_master_config()):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                with pytest.raises(SystemExit) as exc_info:
                    with patch.object(sys, "argv", ["run_hooks"]):
                        from agent.main import run_hooks

                        run_hooks()
                assert exc_info.value.code == 1
