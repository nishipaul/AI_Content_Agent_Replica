"""
Exception and exception-handler tests: AppException, HTTP status, handler registration.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.api.exceptions import (
    AppException,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnprocessableEntityError,
    register_exception_handlers,
)


@pytest.mark.unit
def test_app_exception_defaults() -> None:
    """AppException has message, status_code, code, title."""
    e = AppException("Something broke")
    assert e.message == "Something broke"
    assert e.status_code == 500
    assert e.code == "HTTP_500"
    assert "500" in e.title


@pytest.mark.unit
def test_bad_request_error() -> None:
    """BadRequestError is 400."""
    e = BadRequestError("Invalid input")
    assert e.status_code == 400
    assert e.code == "BAD_REQUEST"
    assert e.title == "Bad Request"


@pytest.mark.unit
def test_forbidden_error() -> None:
    """ForbiddenError is 403."""
    e = ForbiddenError("Forbidden")
    assert e.status_code == 403
    assert e.code == "FORBIDDEN"


@pytest.mark.unit
def test_not_found_error() -> None:
    """NotFoundError is 404."""
    e = NotFoundError("Not found")
    assert e.status_code == 404
    assert e.code == "NOT_FOUND"


@pytest.mark.unit
def test_service_unavailable_error() -> None:
    """ServiceUnavailableError is 503."""
    e = ServiceUnavailableError("Unavailable")
    assert e.status_code == 503


@pytest.mark.unit
def test_unprocessable_entity_error() -> None:
    """UnprocessableEntityError is 422."""
    e = UnprocessableEntityError("Invalid payload")
    assert e.status_code == 422
    assert e.code == "UNPROCESSABLE"
    assert "Unprocessable" in e.title


@pytest.mark.unit
def test_register_exception_handlers_does_not_raise() -> None:
    """register_exception_handlers can be called on a fresh FastAPI app."""
    app = FastAPI()
    register_exception_handlers(app)
    assert len(app.exception_handlers) > 0


@pytest.mark.api
def test_app_exception_returns_correct_status() -> None:
    """Raising AppException in a route results in correct HTTP status and body."""
    from fastapi import APIRouter

    from agent.api.exceptions import AppException

    app = FastAPI()
    register_exception_handlers(app)
    router = APIRouter()

    @router.get("/fail")
    def fail():
        raise AppException("Something broke", status_code=500)

    app.include_router(router)
    c = TestClient(app)
    r = c.get("/fail")
    assert r.status_code == 500
    data = r.json()
    assert "title" in data
    assert "detail" in data
    assert data["detail"] == "Something broke"
