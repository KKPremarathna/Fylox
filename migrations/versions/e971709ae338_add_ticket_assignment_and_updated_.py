"""add ticket assignment and updated timestamp

Revision ID: e971709ae338
Revises: 9b1531c1235f
Create Date: 2026-09-29 18:51:26.193454
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e971709ae338"
down_revision: Union[str, Sequence[str], None] = "9b1531c1235f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("assigned_admin_id", sa.Integer(), nullable=True),
    )

    op.add_column(
        "tickets",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        op.f("ix_tickets_assigned_admin_id"),
        "tickets",
        ["assigned_admin_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_tickets_assigned_admin_id_users",
        "tickets",
        "users",
        ["assigned_admin_id"],
        ["user_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tickets_assigned_admin_id_users",
        "tickets",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_tickets_assigned_admin_id"),
        table_name="tickets",
    )

    op.drop_column("tickets", "updated_at")
    op.drop_column("tickets", "assigned_admin_id")