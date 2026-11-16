from app.catalog.domain.model.aggregates.product import Product
from app.catalog.infrastructure.persistence.models import ProductModel
from app.shared.domain.value_objects import Money


def to_domain(model: ProductModel) -> Product:
    return Product(
        store_id=model.store_id,
        code=model.code,
        description=model.description,
        brand=model.brand,
        category=model.category,
        unit=model.unit,
        cash_price=Money(model.cash_price),
        list_price=Money(model.list_price),
        supplier=model.supplier,
        image_url=model.image_url,
        is_active=model.is_active,
        id=model.id,
    )


def to_model(product: Product) -> ProductModel:
    return ProductModel(
        store_id=product.store_id,
        code=product.code,
        description=product.description,
        brand=product.brand,
        category=product.category,
        unit=product.unit,
        cash_price=product.cash_price.amount,
        list_price=product.list_price.amount,
        supplier=product.supplier,
        image_url=product.image_url,
        is_active=product.is_active,
    )
