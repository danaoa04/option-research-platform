"""Add versioned institutional research artifacts for Sprint 9C."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_institutional_research_layer"
down_revision = "0018_replay_workspace_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institutional_research_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("artifact_id", sa.String(length=128), nullable=False),
        sa.Column("experiment_id", sa.String(length=128), nullable=False),
        sa.Column("artifact_kind", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("replay_links", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artifact_id"),
    )
    op.create_index(
        "ix_institutional_artifacts_experiment",
        "institutional_research_artifacts",
        ["experiment_id", "artifact_kind"],
    )
    op.create_index(
        "ix_institutional_artifacts_created", "institutional_research_artifacts", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_institutional_artifacts_created", table_name="institutional_research_artifacts"
    )
    op.drop_index(
        "ix_institutional_artifacts_experiment", table_name="institutional_research_artifacts"
    )
    op.drop_table("institutional_research_artifacts")
