"""Add durable shared provider operations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_provider_operations"
down_revision = "0019_institutional_research_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(128), nullable=False, unique=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("request_checksum", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_jobs_provider", "provider_jobs", ["provider"])
    op.create_index("ix_provider_jobs_status", "provider_jobs", ["status"])
    op.create_index("ix_provider_jobs_checksum", "provider_jobs", ["request_checksum"])
    op.create_table(
        "provider_job_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(128),
            sa.ForeignKey("provider_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "sequence"),
    )
    op.create_index("ix_provider_events_job", "provider_job_events", ["job_id"])
    op.create_table(
        "provider_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(128),
            sa.ForeignKey("provider_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checkpoint_id", sa.String(128), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("continuation", sa.String(512)),
        sa.Column("response_checksum", sa.String(64), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("job_id", "checkpoint_id"),
    )
    op.create_index("ix_provider_checkpoints_job", "provider_checkpoints", ["job_id"])
    op.create_index(
        "ix_provider_checkpoints_checksum", "provider_checkpoints", ["response_checksum"]
    )
    op.create_table(
        "provider_failures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(128),
            sa.ForeignKey("provider_jobs.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("message", sa.String(2048), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_provider_failures_unresolved", "provider_failures", ["provider", "resolved"]
    )


def downgrade() -> None:
    op.drop_index("ix_provider_failures_unresolved", table_name="provider_failures")
    op.drop_table("provider_failures")
    op.drop_index("ix_provider_checkpoints_checksum", table_name="provider_checkpoints")
    op.drop_index("ix_provider_checkpoints_job", table_name="provider_checkpoints")
    op.drop_table("provider_checkpoints")
    op.drop_index("ix_provider_events_job", table_name="provider_job_events")
    op.drop_table("provider_job_events")
    op.drop_index("ix_provider_jobs_checksum", table_name="provider_jobs")
    op.drop_index("ix_provider_jobs_status", table_name="provider_jobs")
    op.drop_index("ix_provider_jobs_provider", table_name="provider_jobs")
    op.drop_table("provider_jobs")
