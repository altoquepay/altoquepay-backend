"""create users and password_reset_tokens

Revision ID: 8c4e2b7d91a3
Revises: 55a7a1579018
Create Date: 2026-11-12 18:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c4e2b7d91a3"
down_revision: str | Sequence[str] | None = "55a7a1579018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('SYSTEM_ADMIN', 'STORE_ADMIN', 'CUSTOMER')",
            name=op.f("ck_users_role_known"),
        ),
        sa.CheckConstraint(
            "(role = 'STORE_ADMIN') = (store_id IS NOT NULL)",
            name=op.f("ck_users_store_only_for_store_admin"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_reset_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_reset_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"),
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )
    # The users table exists now, so the author of a BCRP cap can reference it.
    op.create_foreign_key(
        op.f("fk_bcrp_caps_created_by_users"), "bcrp_caps", "users", ["created_by"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("fk_bcrp_caps_created_by_users"), "bcrp_caps", type_="foreignkey")
    op.drop_index(op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("users")
