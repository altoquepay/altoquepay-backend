"""Tests for the catalog facade against the migrated PostgreSQL database. Nothing is committed."""

from decimal import Decimal

import pytest

from app.catalog.domain.model.aggregates.product import Product
from app.catalog.infrastructure.persistence.product_repository_impl import ProductRepositoryImpl
from app.catalog.interfaces.acl.catalog_facade import ActiveProduct, CatalogFacade
from app.shared.domain.errors import BusinessError
from app.shared.domain.value_objects import Money
from app.shared.infrastructure.database import session_factory
from app.shared.infrastructure.unit_of_work import UnitOfWork
from tests.stored_store import add_store


@pytest.fixture
async def unit_of_work():
    async with UnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


async def add_product(unit_of_work, store_id: int, code: str, price: str, active=True) -> Product:
    product = Product(
        store_id=store_id,
        code=code,
        description=f"Producto {code}",
        brand="Marca",
        category="Abarrotes",
        unit="unidad",
        cash_price=Money(Decimal(price)),
        list_price=Money(Decimal(price)),
        is_active=active,
    )
    await ProductRepositoryImpl(unit_of_work.session).add(product)
    return product


async def test_active_products_of_the_store_are_returned(unit_of_work):
    store = await add_store(unit_of_work)
    rice = await add_product(unit_of_work, store.id, "ARR-5", "23.9")
    oil = await add_product(unit_of_work, store.id, "ACE-1", "12")

    products = await CatalogFacade(unit_of_work).get_active_products(
        store.id, [oil.id, rice.id, rice.id]
    )

    assert sorted(products, key=lambda product: product.code) == [
        ActiveProduct(oil.id, "ACE-1", "Producto ACE-1", Decimal("12.00")),
        ActiveProduct(rice.id, "ARR-5", "Producto ARR-5", Decimal("23.90")),
    ]


async def test_inactive_foreign_and_missing_products_fail_the_whole_call(unit_of_work):
    store = await add_store(unit_of_work)
    other_store = await add_store(unit_of_work, ruc="20999999991")
    available = await add_product(unit_of_work, store.id, "ARR-5", "23.9")
    inactive = await add_product(unit_of_work, store.id, "ACE-1", "12", active=False)
    foreign = await add_product(unit_of_work, other_store.id, "LEC-1", "4.5")
    missing_id = foreign.id + 1000

    with pytest.raises(BusinessError) as error:
        await CatalogFacade(unit_of_work).get_active_products(
            store.id, [missing_id, available.id, foreign.id, inactive.id]
        )

    assert (error.value.code, error.value.status, error.value.field) == (
        "PRODUCT_NOT_AVAILABLE",
        422,
        "items",
    )
    assert error.value.details == {"product_ids": sorted([inactive.id, foreign.id, missing_id])}


async def test_no_ids_means_no_products(unit_of_work):
    store = await add_store(unit_of_work)

    assert await CatalogFacade(unit_of_work).get_active_products(store.id, []) == []
