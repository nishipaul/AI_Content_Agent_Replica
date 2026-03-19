"""
Tenant module tests: TenantConfigUnavailableError, _ai_config_base_url_or_none.

tenant_exists and _get_connection require real SDK/Vault; tested via mock in API tests.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import pytest

from agent.api.tenant import TenantConfigUnavailableError, _ai_config_base_url_or_none


@pytest.mark.unit
def test_tenant_config_unavailable_error() -> None:
    """TenantConfigUnavailableError has .message and default message."""
    e = TenantConfigUnavailableError()
    assert e.message == "Tenant config service unavailable"
    assert str(e) == e.message

    e2 = TenantConfigUnavailableError("Custom message")
    assert e2.message == "Custom message"


@pytest.mark.unit
def test_ai_config_base_url_from_env() -> None:
    """_ai_config_base_url_or_none returns stripped URL from AI_CONFIG_API_BASE_URL."""
    with patch.dict(
        os.environ, {"AI_CONFIG_API_BASE_URL": "  https://example.com/  "}, clear=False
    ):
        # Need to re-import or reload to pick up env; _ai_config_base_url_or_none reads os.getenv at call time
        url = _ai_config_base_url_or_none()
    assert url == "https://example.com"


@pytest.mark.unit
def test_ai_config_base_url_fallback_keys() -> None:
    """_ai_config_base_url_or_none checks AI_CONFIG_API_URL and ai_config_api_base_url."""
    with patch.dict(
        os.environ,
        {"AI_CONFIG_API_BASE_URL": "", "AI_CONFIG_API_URL": "https://alt.com"},
        clear=False,
    ):
        url = _ai_config_base_url_or_none()
    assert url == "https://alt.com"


@pytest.mark.unit
def test_tenant_exists_raises_when_sdk_missing() -> None:
    """tenant_exists raises TenantConfigUnavailableError when _get_connection raises."""
    import agent.api.tenant as tenant_module

    with patch.object(
        tenant_module,
        "_get_connection",
        side_effect=TenantConfigUnavailableError("SDK not installed"),
    ):
        with pytest.raises(TenantConfigUnavailableError, match="SDK not installed"):
            asyncio.run(tenant_module.tenant_exists("tid", "feat"))


@pytest.mark.unit
def test_tenant_exists_true_when_connection_mocked() -> None:
    """tenant_exists returns True when _get_connection returns mock with get_config True."""
    from unittest.mock import AsyncMock

    import agent.api.tenant as tenant_module

    mock_conn = type("MockConn", (), {})()
    mock_conn.client = type("MockClient", (), {})()
    mock_conn.client.get_config = AsyncMock(return_value=True)

    with patch.object(tenant_module, "_get_connection", return_value=mock_conn):
        result = asyncio.run(tenant_module.tenant_exists("tid", "feat"))
    assert result is True


@pytest.mark.unit
def test_tenant_exists_false_when_connection_mocked() -> None:
    """tenant_exists returns False when get_config returns False."""
    from unittest.mock import AsyncMock

    import agent.api.tenant as tenant_module

    mock_conn = type("MockConn", (), {})()
    mock_conn.client = type("MockClient", (), {})()
    mock_conn.client.get_config = AsyncMock(return_value=False)

    with patch.object(tenant_module, "_get_connection", return_value=mock_conn):
        result = asyncio.run(tenant_module.tenant_exists("tid", "feat"))
    assert result is False
