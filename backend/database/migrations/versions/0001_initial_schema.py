"""Initial historical options database schema."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from backend.database.models import Base

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from backend.database.models import Base

    Base.metadata.drop_all(bind=bind)
