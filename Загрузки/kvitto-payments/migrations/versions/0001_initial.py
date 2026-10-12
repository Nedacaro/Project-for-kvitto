"""таблица tariffs и payments

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),  # копейки
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("tariff_id", sa.String(), sa.ForeignKey("tariffs.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("discount", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("installment_months", sa.Integer(), nullable=True),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("tariffs")
