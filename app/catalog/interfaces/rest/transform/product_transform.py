from app.catalog.domain.model.aggregates.product import Product, ProductDetails
from app.catalog.interfaces.rest.resources.product_resources import (
    ProductDetailsResource,
    ProductResource,
)
from app.shared.domain.value_objects import Money


def to_details(resource: ProductDetailsResource) -> ProductDetails:
    return ProductDetails(
        code=resource.code,
        description=resource.description,
        brand=resource.brand,
        category=resource.category,
        unit=resource.unit,
        cash_price=Money(resource.cash_price),
        list_price=Money(resource.list_price),
        supplier=resource.supplier,
    )


def to_resource(product: Product) -> ProductResource:
    if product.id is None:
        raise ValueError("Only a stored product has a resource.")
    return ProductResource(
        id=product.id,
        code=product.code,
        description=product.description,
        brand=product.brand,
        category=product.category,
        unit=product.unit,
        supplier=product.supplier,
        cash_price=product.cash_price.amount,
        list_price=product.list_price.amount,
        image_url=product.image_url,
        is_active=product.is_active,
    )
