"""add state_log table for audit trail

Revision ID: 0002_add_state_log
Revises: 0001_initial_schema
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_state_log"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "state_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_state_log_ticket_id"), "state_log", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_state_log_creado_en"), "state_log", ["creado_en"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_state_log_creado_en"), table_name="state_log")
    op.drop_index(op.f("ix_state_log_ticket_id"), table_name="state_log")
    op.drop_table("state_log")
