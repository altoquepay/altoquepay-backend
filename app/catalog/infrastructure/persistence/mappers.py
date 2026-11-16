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


def copy_to_model(product: Product, model: ProductModel) -> ProductModel:
    model.store_id = product.store_id
    model.code = product.code
    model.description = product.description
    model.brand = product.brand
    model.category = product.category
    model.unit = product.unit
    model.cash_price = product.cash_price.amount
    model.list_price = product.list_price.amount
    model.supplier = product.supplier
    model.image_url = product.image_url
    model.is_active = product.is_active
    return model
