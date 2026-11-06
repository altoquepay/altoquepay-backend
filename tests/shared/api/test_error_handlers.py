"""Tests for the common error format and the CORS configuration."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app as application
from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.config import get_settings
from app.shared.interfaces.rest.error_handlers import register_error_handlers


class Purchase(BaseModel):
    store_id: int
    password: str


probe_app = FastAPI()
register_error_handlers(probe_app)


@probe_app.get("/business-error")
async def raise_business_error():
    raise BusinessError(
        "CREDIT_LIMIT_EXCEEDED",
        "The purchase exceeds the available credit.",
        field="items",
        details={"available": "120.00"},
    )


@probe_app.get("/conflict")
async def raise_conflict():
    raise BusinessError("PRODUCT_CODE_TAKEN", "Code already in use.", status=409)


@probe_app.get("/unauthorized")
async def raise_unauthorized():
    raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})


@probe_app.get("/unexpected-error")
async def raise_unexpected_error():
    raise RuntimeError("database password is hunter2")


@probe_app.post("/purchases")
async def create_purchase(purchase: Purchase):
    return purchase


@pytest.fixture
def client():
    return TestClient(probe_app, raise_server_exceptions=False)


def test_business_error_uses_the_common_format(client):
    response = client.get("/business-error")
    assert response.status_code == 422
    assert response.json() == {
        "code": "CREDIT_LIMIT_EXCEEDED",
        "message": "The purchase exceeds the available credit.",
        "field": "items",
        "details": {"available": "120.00"},
    }


def test_business_error_can_set_its_status(client):
    assert client.get("/conflict").status_code == 409


def test_validation_error_reports_every_field_without_echoing_the_input(client):
    response = client.post("/purchases", json={"store_id": "abc", "password": "hunter2"})
    missing_body = client.post("/purchases")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["field"] == "store_id"
    assert body["details"]["errors"][0]["field"] == "store_id"
    assert "hunter2" not in response.text
    assert missing_body.json()["field"] is None


def test_http_exception_uses_the_common_format_and_keeps_headers(client):
    response = client.get("/unauthorized")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_route_uses_the_common_format(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_unexpected_error_hides_internal_details(client):
    response = client.get("/unexpected-error")
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "hunter2" not in response.text


def test_application_allows_only_configured_cors_origins():
    client = TestClient(application)
    allowed_origin = get_settings().cors_origins_list[0]
    request_headers = {"Access-Control-Request-Method": "GET"}

    allowed = client.options("/health", headers={"Origin": allowed_origin, **request_headers})
    rejected = client.options(
        "/health", headers={"Origin": "https://evil.example", **request_headers}
    )

    assert allowed.headers["access-control-allow-origin"] == allowed_origin
    assert "access-control-allow-origin" not in rejected.headers
