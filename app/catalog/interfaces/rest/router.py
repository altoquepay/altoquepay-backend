from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile

from app.catalog.application.command_services.product_command_service import (
    ProductCommandService,
)
from app.catalog.application.query_services.product_query_service import ProductQueryService
from app.catalog.domain.repositories.product_repository import ProductFilter
from app.catalog.domain.services.product_image import MAXIMUM_IMAGE_BYTES
from app.catalog.interfaces.rest.dependencies import (
    get_product_command_service,
    get_product_query_service,
)
from app.catalog.interfaces.rest.resources.product_resources import (
    ProductDetailsResource,
    ProductResource,
)
from app.catalog.interfaces.rest.transform.product_transform import to_details, to_resource
from app.shared.interfaces.rest.pagination import Page, PageParams
from app.shared.interfaces.rest.security import get_store_id

router = APIRouter(prefix="/products", tags=["Products"])

StoreId = Annotated[int, Depends(get_store_id)]
QueryService = Annotated[ProductQueryService, Depends(get_product_query_service)]
CommandService = Annotated[ProductCommandService, Depends(get_product_command_service)]


@router.get("")
async def list_products(
    store_id: StoreId,
    params: Annotated[PageParams, Query()],
    query_service: QueryService,
    search: Annotated[str | None, Query(max_length=100)] = None,
    active: bool | None = None,
) -> Page[ProductResource]:
    """List the store's products by code. search matches the code or the description."""
    products, total = await query_service.list_page(
        store_id, ProductFilter(search, active), params.offset, params.size
    )
    return Page(
        items=[to_resource(product) for product in products],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post("", status_code=201)
async def create_product(
    resource: ProductDetailsResource, store_id: StoreId, command_service: CommandService
) -> ProductResource:
    """Add a product. Its code must be unique in the store."""
    return to_resource(await command_service.create(store_id, to_details(resource)))


@router.get("/{product_id}")
async def get_product(
    product_id: int, store_id: StoreId, query_service: QueryService
) -> ProductResource:
    return to_resource(await query_service.get(store_id, product_id))


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    resource: ProductDetailsResource,
    store_id: StoreId,
    command_service: CommandService,
) -> ProductResource:
    """Replace the product's details. Registered purchases keep the price they copied."""
    product = await command_service.update(store_id, product_id, to_details(resource))
    return to_resource(product)


@router.patch("/{product_id}/deactivate")
async def deactivate_product(
    product_id: int, store_id: StoreId, command_service: CommandService
) -> ProductResource:
    """Stop selling the product. It stays listed, and past purchases are not changed."""
    return to_resource(await command_service.deactivate(store_id, product_id))


@router.post("/{product_id}/image")
async def upload_product_image(
    product_id: int, image: UploadFile, store_id: StoreId, command_service: CommandService
) -> ProductResource:
    """Upload a JPEG, PNG or WebP image of up to 2 MB as multipart/form-data, field image.

    It replaces the previous image.
    """
    # One byte over the limit is enough to know the file is too large.
    content = await image.read(MAXIMUM_IMAGE_BYTES + 1)
    return to_resource(await command_service.change_image(store_id, product_id, content))
