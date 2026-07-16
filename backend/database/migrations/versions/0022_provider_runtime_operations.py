"""Add provider runtime operational state without secret payloads."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022_provider_runtime_operations"
down_revision = "0021_provider_operations_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_runtime_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state_id", sa.String(128), nullable=False, unique=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("state_kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "state_kind", "state_id"),
    )
    op.create_index(
        "ix_provider_runtime_provider_kind",
        "provider_runtime_state",
        ["provider", "state_kind"],
    )
    op.create_index("ix_provider_runtime_status", "provider_runtime_state", ["status"])


def downgrade() -> None:
    op.drop_index("ix_provider_runtime_status", table_name="provider_runtime_state")
    op.drop_index("ix_provider_runtime_provider_kind", table_name="provider_runtime_state")
    op.drop_table("provider_runtime_state")
