from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('SYSTEM_ADMIN', 'STORE_ADMIN', 'CUSTOMER')", name="role_known"),
        CheckConstraint(
            "(role = 'STORE_ADMIN') = (store_id IS NOT NULL)", name="store_only_for_store_admin"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The email of an administrator, or the DNI of a customer.
    username: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    # shortcut: no foreign key until the stores context creates the stores table; add it then.
    store_id: Mapped[int | None]
    must_change_password: Mapped[bool]
    is_active: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # SHA-256 of the token in hexadecimal; the token itself only travels in the email.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
