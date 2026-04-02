"""Shared API error payload helpers for consistent HTTPException detail shape."""

from typing import Any

from fastapi import HTTPException


def build_error_detail(
    code: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return canonical error detail payload for API responses."""
    return {
        "error": {
            "code": code,
            "message": message,
            "context": context or {},
        }
    }


def api_error(
    status_code: int,
    code: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> HTTPException:
    """Construct HTTPException with canonical error payload."""
    return HTTPException(
        status_code=status_code,
        detail=build_error_detail(code=code, message=message, context=context),
    )
