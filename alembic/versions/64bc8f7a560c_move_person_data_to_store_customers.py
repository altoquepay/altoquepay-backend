"""move person data to store_customers

Revision ID: 64bc8f7a560c
Revises: e5b19d4c7a32
Create Date: 2026-11-17 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "64bc8f7a560c"
down_revision: str | Sequence[str] | None = "e5b19d4c7a32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERSON_COLUMNS = (
    ("first_names", sa.String(length=100)),
    ("last_names", sa.String(length=100)),
    ("phone", sa.String(length=20)),
    ("address", sa.String(length=200)),
)


def upgrade() -> None:
    """Upgrade schema."""
    for name, column_type in PERSON_COLUMNS:
        op.add_column("store_customers", sa.Column(name, column_type, nullable=True))
    # Every store starts from what the person's data was; from now on each edits its own copy.
    op.execute(
        "UPDATE store_customers SET first_names = c.first_names, last_names = c.last_names, "
        "phone = c.phone, address = c.address FROM customers c "
        "WHERE c.id = store_customers.customer_id"
    )
    for name in ("first_names", "last_names"):
        op.alter_column("store_customers", name, nullable=False)
    for name, _column_type in PERSON_COLUMNS:
        op.drop_column("customers", name)


def downgrade() -> None:
    """Downgrade schema."""
    for name, column_type in PERSON_COLUMNS:
        op.add_column("customers", sa.Column(name, column_type, nullable=True))
    # The shared data comes back from the oldest account, the store that registered the person.
    op.execute(
        "UPDATE customers SET first_names = a.first_names, last_names = a.last_names, "
        "phone = a.phone, address = a.address FROM ("
        "SELECT DISTINCT ON (customer_id) customer_id, first_names, last_names, phone, address "
        "FROM store_customers ORDER BY customer_id, id"
        ") a WHERE a.customer_id = customers.id"
    )
    for name in ("first_names", "last_names"):
        op.alter_column("customers", name, nullable=False)
    for name, _column_type in PERSON_COLUMNS:
        op.drop_column("store_customers", name)
