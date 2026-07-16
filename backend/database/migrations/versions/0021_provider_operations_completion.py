"""Add immutable provider operational artifacts for Sprint 10D.1."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_provider_operations_completion"
down_revision = "0020_provider_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_operational_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("artifact_id", sa.String(128), nullable=False, unique=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column(
            "job_id",
            sa.String(128),
            sa.ForeignKey("provider_jobs.job_id", ondelete="CASCADE"),
        ),
        sa.Column("artifact_kind", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_provider_artifacts_provider_kind",
        "provider_operational_artifacts",
        ["provider", "artifact_kind"],
    )
    op.create_index("ix_provider_artifacts_job", "provider_operational_artifacts", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_provider_artifacts_job", table_name="provider_operational_artifacts")
    op.drop_index(
        "ix_provider_artifacts_provider_kind", table_name="provider_operational_artifacts"
    )
    op.drop_table("provider_operational_artifacts")
