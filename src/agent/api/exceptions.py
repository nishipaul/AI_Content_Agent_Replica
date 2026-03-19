"""
Custom exceptions and global exception handlers for consistent HTTP error responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from agent.api.schemas import ErrorDetail
from agent.utils.logging_config import get_logger_without_crew_context

logger = get_logger_without_crew_context("exceptions")


# ----- Custom app exceptions -----


class AppException(Exception):
    """Base exception for application errors with HTTP semantics."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str | None = None,
        title: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or f"HTTP_{status_code}"
        self.title = title or f"Error {status_code}"
        super().__init__(message)


class BadRequestError(AppException):
    """400 Bad Request."""

    def __init__(self, message: str, code: str = "BAD_REQUEST", **kwargs: object):
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            title="Bad Request",
            **kwargs,
        )


class ForbiddenError(AppException):
    """403 Forbidden."""

    def __init__(self, message: str = "Forbidden", **kwargs: object):
        super().__init__(
            message,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Forbidden",
            **kwargs,
        )


class NotFoundError(AppException):
    """404 Not Found."""

    def __init__(self, message: str = "Resource not found", **kwargs: object):
        super().__init__(
            message,
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            title="Not Found",
            **kwargs,
        )


class UnprocessableEntityError(AppException):
    """422 Unprocessable Entity."""

    def __init__(self, message: str, code: str = "UNPROCESSABLE", **kwargs: object):
        super().__init__(
            message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=code,
            title="Unprocessable Entity",
            **kwargs,
        )


class ServiceUnavailableError(AppException):
    """503 Service Unavailable."""

    def __init__(
        self, message: str = "Service temporarily unavailable", **kwargs: object
    ):
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SERVICE_UNAVAILABLE",
            title="Service Unavailable",
            **kwargs,
        )


# ----- Response builder -----


def _error_response(
    request: Request,
    status_code: int,
    title: str,
    detail: str | None = None,
    code: str | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    body = ErrorDetail(
        type="about:blank",
        title=title,
        status=status_code,
        detail=detail,
        code=code or f"HTTP_{status_code}",
        trace_id=trace_id or getattr(request.state, "trace_id", None),
        timestamp=datetime.now(timezone.utc).isoformat(),
        instance=str(request.url.path) if request else None,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
    )


# ----- Handlers -----


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning("app_exception", message=exc.message)
        return _error_response(
            request,
            exc.status_code,
            exc.title,
            detail=exc.message,
            code=exc.code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Flatten Pydantic validation errors into a readable message
        details = exc.errors()
        parts = [
            " → ".join(str(loc) for loc in e.get("loc", ())) + ": " + e.get("msg", "")
            for e in details
        ]
        detail = "; ".join(parts) if parts else str(exc)
        logger.debug("validation_error", detail=detail)
        return _error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation Error",
            detail=detail,
            code="VALIDATION_ERROR",
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        detail = exc.json() if hasattr(exc, "json") else str(exc)
        return _error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation Error",
            detail=detail,
            code="VALIDATION_ERROR",
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), exc_info=True)
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
            detail="An unexpected error occurred.",
            code="INTERNAL_ERROR",
        )
