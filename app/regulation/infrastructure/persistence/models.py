from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, literal_column
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class BcrpCapModel(Base):
    __tablename__ = "bcrp_caps"
    __table_args__ = (
        CheckConstraint("max_tea > 0", name="max_tea_positive"),
        CheckConstraint("valid_to >= valid_from", name="validity_period_ordered"),
        # Two caps can never be in force on the same day, even if registered at the same time.
        ExcludeConstraint(
            (literal_column("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_bcrp_caps_validity_period",
            using="gist",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # A percentage, as shown to users: 75% is stored as 75.0000000.
    max_tea: Mapped[Decimal] = mapped_column(Numeric(12, 7))
    valid_from: Mapped[date]
    valid_to: Mapped[date]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
