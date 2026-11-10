"""make_ticket_messages_sender_id_nullable

Revision ID: b4a0cc64fcbe
Revises: 5951f34e5241
Create Date: 2026-11-10 14:18:36.384561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4a0cc64fcbe"
down_revision: Union[str, Sequence[str], None] = "5951f34e5241"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    1. Make ticket_messages.sender_id nullable first so it can receive NULLs.
    2. Update any existing AI messages so sender_id is explicitly NULL.
    3. Add a check constraint enforcing that AI messages have NULL sender_id
       and human messages (CUSTOMER, ADMIN) have a non-null sender_id.
    """
    with op.batch_alter_table("ticket_messages") as batch_op:
        batch_op.alter_column(
            "sender_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    op.execute(
        sa.text(
            "UPDATE ticket_messages SET sender_id = NULL WHERE sender_type = 'AI'"
        )
    )

    with op.batch_alter_table("ticket_messages") as batch_op:
        batch_op.create_check_constraint(
            "ck_ticket_messages_sender_attribution",
            "(sender_type = 'AI' AND sender_id IS NULL) OR (sender_type != 'AI' AND sender_id IS NOT NULL)",
        )


def downgrade() -> None:
    """
    Safe downgrade policy:
    Restoring NOT NULL is strictly refused if any AI-authored messages (sender_id IS NULL)
    exist in the database, because restoring NOT NULL would either cause migration failure,
    require deleting customer/AI conversation history, or require fabricating human user attribution.
    Only if zero NULL sender_id rows exist can NOT NULL be restored.
    """
    conn = op.get_bind()
    null_count = conn.execute(
        sa.text("SELECT COUNT(*) FROM ticket_messages WHERE sender_id IS NULL")
    ).scalar()

    if null_count and null_count > 0:
        raise RuntimeError(
            f"Refusing downgrade: {null_count} ticket_messages record(s) have sender_id IS NULL (AI messages). "
            "Restoring NOT NULL constraint would require deleting messages or fabricating user attribution."
        )

    with op.batch_alter_table("ticket_messages") as batch_op:
        batch_op.drop_constraint(
            "ck_ticket_messages_sender_attribution",
            type_="check",
        )
        batch_op.alter_column(
            "sender_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
