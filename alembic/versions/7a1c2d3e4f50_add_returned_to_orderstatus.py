"""add RETURNED to the orderstatus enum

Revision ID: 7a1c2d3e4f50
Revises: b2c3d4e5f6a7
"""
from alembic import op

revision = "7a1c2d3e4f50"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block on older PostgreSQL versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'RETURNED'")


def downgrade() -> None:
    # PostgreSQL cannot drop a single enum value. Leaving it in place is harmless.
    pass
