"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.billing.interfaces.rest.router import router as billing_router
from app.catalog.interfaces.rest.router import router as catalog_router
from app.credit.interfaces.rest.router import router as credit_router
from app.customers.interfaces.rest.router import router as customers_router
from app.iam.infrastructure.first_admin import create_first_system_admin
from app.iam.interfaces.rest.router import router as iam_router
from app.regulation.interfaces.rest.router import router as regulation_router
from app.shared.infrastructure.config import get_settings
from app.shared.infrastructure.database import engine
from app.shared.interfaces.rest.error_handlers import register_error_handlers
from app.stores.interfaces.rest.router import router as stores_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await create_first_system_admin()
    yield
    await engine.dispose()


app = FastAPI(title="AlToque Pay API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(iam_router, prefix="/api/v1")
app.include_router(regulation_router, prefix="/api/v1")
app.include_router(stores_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(credit_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")

# Uploaded files, such as product images. The folder must exist before StaticFiles reads it.
media_dir = Path(get_settings().media_dir)
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")


@app.get("/health")
async def health() -> dict[str, str]:
    """Report that the API is up and able to serve requests."""
    return {"status": "ok"}
