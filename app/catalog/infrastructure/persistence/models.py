from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class ProductModel(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store_id", "code", name="uq_products_store_code"),
        CheckConstraint("cash_price >= 0", name="cash_price_not_negative"),
        CheckConstraint("list_price >= 0", name="list_price_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    code: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(String(200))
    supplier: Mapped[str | None] = mapped_column(String(100))
    brand: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20))
    image_url: Mapped[str | None] = mapped_column(String(500))
    cash_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # The price on credit, which purchases charge.
    list_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Products are deactivated, never deleted, since past purchases reference them.
    is_active: Mapped[bool] = mapped_column(server_default="true")


class ProductImageModel(Base):
    """The uploaded image files, kept in the database so they survive every redeploy."""

    __tablename__ = "product_images"

    # The name in the image's URL: <store id>/<product id>-<random>.<extension>.
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
