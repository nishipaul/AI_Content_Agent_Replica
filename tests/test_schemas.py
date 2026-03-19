"""
Schema tests: request/response validation, field validators.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.api.schemas import (
    AgentDataRequest,
    AgentDataResponse,
    ErrorDetail,
    HealthResponse,
    ProbeResponse,
)
from agent.crew import Insight, SurveySummaryWithComments


@pytest.mark.unit
def test_health_response() -> None:
    """HealthResponse accepts service, status, version."""
    r = HealthResponse(service="Test", status="healthy", version="1.0.0")
    assert r.service == "Test"
    assert r.status == "healthy"
    assert r.version == "1.0.0"


@pytest.mark.unit
def test_probe_response() -> None:
    """ProbeResponse accepts status ok."""
    r = ProbeResponse(status="ok")
    assert r.status == "ok"


@pytest.mark.unit
def test_agent_data_request_strip_tenant_fields() -> None:
    """AgentDataRequest strips whitespace from smtip_tid, smtip_feature, model."""
    r = AgentDataRequest(
        locale="en-US",
        survey_data={"survey_id": "s", "responses": []},
        smtip_tid="  tid  ",
        smtip_feature="  feature  ",
        model="  auto-route  ",
    )
    assert r.smtip_tid == "tid"
    assert r.smtip_feature == "feature"
    assert r.model == "auto-route"


@pytest.mark.unit
def test_agent_data_request_minimal() -> None:
    """AgentDataRequest with minimal required fields; optional default None/empty."""
    r = AgentDataRequest(
        locale="en-US",
        survey_data={"survey_id": "s", "survey_name": "n", "responses": []},
        smtip_tid="tid",
        smtip_feature="feat",
        model="auto-route",
    )
    assert r.user_id is None
    assert r.session_id is None
    assert r.tags is None


@pytest.mark.unit
def test_agent_data_request_missing_required_raises() -> None:
    """AgentDataRequest raises ValidationError when required fields missing."""
    with pytest.raises(ValidationError):
        AgentDataRequest(
            locale="en-US",
            survey_data={},
            smtip_tid="t",
            # missing smtip_feature, model
        )


@pytest.mark.unit
def test_agent_data_response_success() -> None:
    """AgentDataResponse with success and content."""
    content = SurveySummaryWithComments(
        summary="S",
        insights=[Insight(content="I", comment_ids=["c1"])],
        recommendations=["R"],
    )
    r = AgentDataResponse(
        id="test-id", success=True, content=content, error=None, latency_seconds=1.0
    )
    assert r.success is True
    assert r.content == content
    assert r.error is None
    assert r.latency_seconds == 1.0


@pytest.mark.unit
def test_agent_data_response_failure() -> None:
    """AgentDataResponse with success=False and error."""
    r = AgentDataResponse(
        id="test-id",
        success=False,
        content=None,
        error="Something failed",
        latency_seconds=0.5,
    )
    assert r.success is False
    assert r.content is None
    assert r.error == "Something failed"


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_value,expected",
    [
        (None, None),
        ("low", "low"),
        ("  LOW  ", "low"),
        ("Medium", "medium"),
        ("HIGH", "high"),
    ],
)
def test_survey_data_request_reasoning_effort_valid(
    raw_value: str | None, expected: str | None
) -> None:
    """reasoning_effort accepts None and valid values (case/whitespace insensitive)."""
    kwargs: dict = {
        "locale": "en-US",
        "survey_data": {"survey_id": "s", "responses": []},
        "smtip_tid": "t",
        "smtip_feature": "f",
        "model": "m",
    }
    if raw_value is not None:
        kwargs["reasoning_effort"] = raw_value
    r = AgentDataRequest(**kwargs)
    assert r.reasoning_effort == expected


@pytest.mark.unit
@pytest.mark.parametrize("bad_value", ["invalid", "super", ""])
def test_survey_data_request_reasoning_effort_invalid(bad_value: str) -> None:
    """reasoning_effort rejects values outside {low, medium, high}."""
    with pytest.raises(ValidationError, match="reasoning_effort"):
        AgentDataRequest(
            locale="en-US",
            survey_data={"survey_id": "s", "responses": []},
            smtip_tid="t",
            smtip_feature="f",
            model="m",
            reasoning_effort=bad_value,
        )


@pytest.mark.unit
def test_error_detail() -> None:
    """ErrorDetail accepts title, status, and optional detail, code, trace_id, timestamp, instance."""
    e = ErrorDetail(title="Bad Request", status=400)
    assert e.title == "Bad Request"
    assert e.status == 400
    assert e.type == "about:blank"
    assert e.detail is None

    e2 = ErrorDetail(
        title="Validation Error",
        status=422,
        detail="Invalid field",
        code="VALIDATION_ERROR",
        trace_id="tid-1",
        instance="/v1/survey-summary",
    )
    assert e2.detail == "Invalid field"
    assert e2.code == "VALIDATION_ERROR"
    assert e2.trace_id == "tid-1"
    assert e2.instance == "/v1/survey-summary"
