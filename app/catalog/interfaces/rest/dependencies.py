from pathlib import Path
from typing import Annotated

from fastapi import Depends

from app.catalog.application.command_services.product_command_service import (
    ProductCommandService,
)
from app.catalog.application.ports.image_storage import ImageStorage
from app.catalog.application.query_services.product_query_service import ProductQueryService
from app.catalog.infrastructure.persistence.product_repository_impl import ProductRepositoryImpl
from app.catalog.infrastructure.storage.local_image_storage import LocalImageStorage
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.unit_of_work import UnitOfWork, get_unit_of_work


def get_image_storage() -> ImageStorage:
    return LocalImageStorage(Path(get_settings().media_dir))


def get_product_command_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    images: Annotated[ImageStorage, Depends(get_image_storage)],
) -> ProductCommandService:
    return ProductCommandService(ProductRepositoryImpl(unit_of_work.session), images, unit_of_work)


def get_product_query_service(
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ProductQueryService:
    return ProductQueryService(ProductRepositoryImpl(unit_of_work.session))
