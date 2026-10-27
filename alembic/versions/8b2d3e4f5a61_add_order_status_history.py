"""add order_status_history

Revision ID: 8b2d3e4f5a61
Revises: 7a1c2d3e4f50
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8b2d3e4f5a61"
down_revision = "7a1c2d3e4f50"
branch_labels = None
depends_on = None

STATUS = postgresql.ENUM(
    "RECEIVED", "PROCESSING", "FULFILLED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED",
    name="orderstatus", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("status", STATUS, nullable=False),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_order_status_history_id"), "order_status_history", ["id"])
    op.create_index(op.f("ix_order_status_history_order_id"), "order_status_history", ["order_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_order_status_history_order_id"), table_name="order_status_history")
    op.drop_index(op.f("ix_order_status_history_id"), table_name="order_status_history")
    op.drop_table("order_status_history")
