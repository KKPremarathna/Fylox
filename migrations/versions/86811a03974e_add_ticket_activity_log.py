"""add ticket activity log

Revision ID: 86811a03974e
Revises: e971709ae338
Create Date: 2026-09-29 20:21:54.713615
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "86811a03974e"
down_revision: Union[str, Sequence[str], None] = "e971709ae338"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.user_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_ticket_activities_actor_id"),
        "ticket_activities",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_activities_event_type"),
        "ticket_activities",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_activities_id"),
        "ticket_activities",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_activities_ticket_id"),
        "ticket_activities",
        ["ticket_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ticket_activities_ticket_id"),
        table_name="ticket_activities",
    )
    op.drop_index(
        op.f("ix_ticket_activities_id"),
        table_name="ticket_activities",
    )
    op.drop_index(
        op.f("ix_ticket_activities_event_type"),
        table_name="ticket_activities",
    )
    op.drop_index(
        op.f("ix_ticket_activities_actor_id"),
        table_name="ticket_activities",
    )
    op.drop_table("ticket_activities")