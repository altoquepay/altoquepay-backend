"""Tests for the pagination parameters and response body."""

from decimal import Decimal
from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.shared.interfaces.rest.pagination import Page, PageParams


class Product(BaseModel):
    price: Decimal


probe_app = FastAPI()


@probe_app.get("/products")
async def list_products(params: Annotated[PageParams, Query()]) -> Page[Product]:
    return Page(
        items=[Product(price=Decimal("356.04"))],
        total=params.offset,
        page=params.page,
        size=params.size,
    )


client = TestClient(probe_app)


def test_defaults_to_the_first_page_of_twenty():
    assert client.get("/products").json() == {
        "items": [{"price": "356.04"}],
        "total": 0,
        "page": 1,
        "size": 20,
    }


def test_offset_skips_previous_pages():
    assert client.get("/products", params={"page": 3, "size": 10}).json()["total"] == 20


@pytest.mark.parametrize("invalid_params", [{"page": 0}, {"size": 0}, {"size": 101}])
def test_rejects_out_of_range_params(invalid_params):
    assert client.get("/products", params=invalid_params).status_code == 422
