from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class StoreModel(Base):
    __tablename__ = "stores"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status_known"),
        CheckConstraint("default_cutoff_day BETWEEN 1 AND 25", name="default_cutoff_day_range"),
        CheckConstraint("default_payment_day BETWEEN 1 AND 28", name="default_payment_day_range"),
        CheckConstraint(
            "default_payment_day > default_cutoff_day", name="default_payment_day_after_cutoff"
        ),
        CheckConstraint("default_tea >= 0", name="default_tea_not_negative"),
        CheckConstraint("default_late_tea >= 0", name="default_late_tea_not_negative"),
        CheckConstraint("default_max_weeks BETWEEN 1 AND 99", name="default_max_weeks_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(150))
    ruc: Mapped[str] = mapped_column(String(11), unique=True)
    address: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    default_cutoff_day: Mapped[int]
    default_payment_day: Mapped[int]
    # Percentages, as shown to users: 40% is stored as 40.0000000.
    default_tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    default_late_tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    default_max_weeks: Mapped[int]
