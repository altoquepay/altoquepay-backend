"""Global exception handlers that give every error response the same body."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.shared.domain.errors import BusinessError


def error_response(
    status: int,
    code: str,
    message: str,
    field: str | None = None,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "field": field, "details": details},
        headers=headers,
    )


async def handle_business_error(_request: Request, error: BusinessError) -> JSONResponse:
    return error_response(error.status, error.code, error.message, error.field, error.details)


def invalid_field_name(validation_error: dict[str, Any]) -> str | None:
    # A malformed JSON body is located by a character position, which is not a field.
    if validation_error["type"] == "json_invalid":
        return None
    # The first location item is the request part ("body", "query"...), not a field name.
    return ".".join(map(str, validation_error["loc"][1:])) or None


async def handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    # Copies only location and message: the raw errors echo the input, which may hold passwords.
    invalid_fields = [
        {"field": invalid_field_name(item), "message": item["msg"]} for item in error.errors()
    ]
    first_invalid_field = invalid_fields[0]
    return error_response(
        422,
        "VALIDATION_ERROR",
        first_invalid_field["message"],
        first_invalid_field["field"],
        {"errors": invalid_fields},
    )


async def handle_http_exception(_request: Request, error: HTTPException) -> JSONResponse:
    return error_response(
        error.status_code,
        HTTPStatus(error.status_code).name,
        str(error.detail),
        headers=error.headers,
    )


async def handle_unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
    """Hide internal details from the client. The server still logs the traceback."""
    # shortcut: 500 responses skip CORSMiddleware, so browsers hide their body from Angular;
    # add a middleware that catches exceptions if the frontend must read it.
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BusinessError, handle_business_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
