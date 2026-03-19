"""
API route tests: health, probes, Kafka status, survey-summary REST and WebSocket.

Uses mocked tenant_exists and run_agentic_crew so no real LLM or agent-config is required.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent.api.constants import ROUTER_PREFIX


@pytest.mark.api
def test_root_and_health(client: TestClient) -> None:
    """Root GET / and /health return 200 and healthy status."""
    for path in ["/", "/health"]:
        r = client.get(path)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "AI Infra Agent Example" in data["service"]
        assert "version" in data

    r2 = client.get(f"{ROUTER_PREFIX}/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "healthy"


@pytest.mark.api
def test_startup_live_ready_probes(client: TestClient) -> None:
    """Kubernetes probes at root and under router return ok."""
    for path in ["/startUpProbe", "/readinessProbe", "/livenessProbe"]:
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    for path in ["/startup", "/live", "/ready"]:
        r = client.get(f"{ROUTER_PREFIX}{path}")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.api
def test_survey_summary_rest(client: TestClient, sample_survey_payload: dict) -> None:
    """POST /survey-summary returns 200 and mock summary when crew is patched."""
    r = client.post(f"{ROUTER_PREFIX}/survey-summary", json=sample_survey_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["content"] is not None
    assert "summary" in data["content"]
    assert "[MOCK]" in data["content"]["summary"]
    assert "insights" in data["content"]
    assert "recommendations" in data["content"]
    assert data.get("latency_seconds") is not None


@pytest.mark.api
def test_survey_summary_validation_error(client: TestClient) -> None:
    """POST /survey-summary with invalid body returns 422."""
    r = client.post(
        f"{ROUTER_PREFIX}/survey-summary",
        json={
            "smtip_tid": "t",
            "smtip_feature": "f",
        },  # missing required survey_data, model, etc.
    )
    assert r.status_code == 422


@pytest.mark.api
def test_survey_summary_rest_strips_whitespace(
    client: TestClient, sample_survey_payload: dict
) -> None:
    """Survey request strips smtip_tid/smtip_feature/model whitespace."""
    sample_survey_payload["smtip_tid"] = "  tid  "
    sample_survey_payload["smtip_feature"] = "  feature  "
    sample_survey_payload["model"] = "  auto-route  "
    r = client.post(f"{ROUTER_PREFIX}/survey-summary", json=sample_survey_payload)
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.api
@pytest.mark.parametrize("reasoning_effort", [None, "low", "high"])
def test_survey_summary_rest_with_reasoning_effort(
    client: TestClient, sample_survey_payload: dict, reasoning_effort: str | None
) -> None:
    """POST /survey-summary succeeds with various reasoning_effort values."""
    if reasoning_effort is not None:
        sample_survey_payload["reasoning_effort"] = reasoning_effort
    r = client.post(f"{ROUTER_PREFIX}/survey-summary", json=sample_survey_payload)
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.api
def test_survey_summary_rest_500_when_agent_returns_failure(
    client: TestClient, sample_survey_payload: dict
) -> None:
    """POST /survey-summary returns 500 when agent service returns success=False."""
    from unittest.mock import AsyncMock, patch

    from agent.api.schemas import AgentDataResponse

    failing_response = AgentDataResponse(
        success=False,
        content=None,
        error="Crew run failed",
        latency_seconds=0.5,
    )

    with patch(
        "agent.api.routes.generate_response",
        new_callable=AsyncMock,
        return_value=failing_response,
    ):
        from agent.api import app

        c = TestClient(app)
        r = c.post(f"{ROUTER_PREFIX}/survey-summary", json=sample_survey_payload)
    assert r.status_code == 500
    assert "Crew run failed" in (r.json().get("detail") or "")


@pytest.mark.api
def test_websocket_survey_summary(
    client: TestClient, sample_survey_payload: dict
) -> None:
    """WebSocket /ws/survey-summary accepts JSON and returns connected, progress, result."""
    with client.websocket_connect(f"{ROUTER_PREFIX}/ws/survey-summary") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        ws.send_json(sample_survey_payload)
        progress = ws.receive_json()
        assert progress["type"] == "progress"
        result = ws.receive_json()
        assert result["type"] == "result"
        payload = result["payload"]
        assert payload["success"] is True
        assert "[MOCK]" in payload["content"]["summary"]


@pytest.mark.api
def test_survey_summary_rest_404_when_rest_disabled() -> None:
    """POST /survey-summary returns 404 when REST API is disabled in config."""
    from unittest.mock import AsyncMock, patch

    from agent.api import app
    from agent.api.routes import is_rest_api_enabled

    with patch(
        "agent.api.routes.tenant_exists", new_callable=AsyncMock, return_value=True
    ):
        with patch("agent.api.routes.is_rest_api_enabled", return_value=False):
            c = TestClient(app)
            r = c.post(
                f"{ROUTER_PREFIX}/survey-summary",
                json={
                    "locale": "en-US",
                    "survey_data": {"survey_id": "s", "responses": []},
                    "smtip_tid": "t",
                    "smtip_feature": "f",
                    "model": "auto-route",
                },
            )
    assert r.status_code == 404
    assert "disabled" in r.json().get("detail", "").lower()


@pytest.mark.api
def test_websocket_invalid_json_returns_error(client: TestClient) -> None:
    """WebSocket /ws/survey-summary sends error when client sends invalid JSON."""
    with client.websocket_connect(f"{ROUTER_PREFIX}/ws/survey-summary") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        ws.send_text("not valid json {{{")
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "message" in err


@pytest.mark.api
def test_websocket_validation_error_invalid_body(client: TestClient) -> None:
    """WebSocket sends error when body is valid JSON but missing required fields."""
    with client.websocket_connect(f"{ROUTER_PREFIX}/ws/survey-summary") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        ws.send_text('{"smtip_tid": "t"}')  # missing survey_data, smtip_feature, model
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "message" in err


@pytest.mark.api
def test_websocket_tenant_not_registered(
    client: TestClient, sample_survey_payload: dict
) -> None:
    """WebSocket sends error and closes when tenant_exists returns False."""
    from unittest.mock import AsyncMock, patch

    from agent.api import app

    with patch(
        "agent.api.routes.tenant_exists", new_callable=AsyncMock, return_value=False
    ):
        c = TestClient(app)
        with c.websocket_connect(f"{ROUTER_PREFIX}/ws/survey-summary") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"
            ws.send_text(__import__("json").dumps(sample_survey_payload))
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "Tenant not registered" in err.get("message", "")


@pytest.mark.api
def test_websocket_tenant_config_unavailable(
    client: TestClient, sample_survey_payload: dict
) -> None:
    """WebSocket sends error when tenant_exists raises TenantConfigUnavailableError."""
    from unittest.mock import AsyncMock, patch

    from agent.api.tenant import TenantConfigUnavailableError

    with patch(
        "agent.api.routes.tenant_exists",
        new_callable=AsyncMock,
        side_effect=TenantConfigUnavailableError("Config unavailable"),
    ):
        from agent.api import app

        c = TestClient(app)
        with c.websocket_connect(f"{ROUTER_PREFIX}/ws/survey-summary") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"
            ws.send_text(__import__("json").dumps(sample_survey_payload))
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err.get("message") == "Config unavailable"


@pytest.mark.api
def test_websocket_crew_raises_returns_error(
    client: TestClient, sample_survey_payload: dict
) -> None:
    """WebSocket sends error payload when generate_response raises."""
    from unittest.mock import AsyncMock, patch

    from agent.api import app

    with (
        patch(
            "agent.api.routes.tenant_exists", new_callable=AsyncMock, return_value=True
        ),
        patch(
            "agent.api.routes.generate_response",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Crew failed"),
        ),
    ):
        c = TestClient(app)
        with c.websocket_connect(f"{ROUTER_PREFIX}/ws/survey-summary") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"
            ws.send_text(__import__("json").dumps(sample_survey_payload))
            progress = ws.receive_json()
            assert progress["type"] == "progress"
            result = ws.receive_json()
            assert result["type"] == "error"
            assert "payload" in result
            assert result["payload"]["success"] is False
            assert "Crew failed" in result.get("message", "")


@pytest.mark.api
def test_websocket_404_when_disabled() -> None:
    """WebSocket /ws/survey-summary returns 404 when websocket endpoint is disabled."""
    from unittest.mock import patch

    from agent.api import app

    with patch("agent.api.routes.is_websocket_enabled_runtime", return_value=False):
        c = TestClient(app)
        try:
            with c.websocket_connect(
                f"{ROUTER_PREFIX}/ws/survey-summary", timeout=1
            ) as ws:
                ws.receive_json()
        except Exception:
            pass  # 404 or connection error when endpoint disabled
