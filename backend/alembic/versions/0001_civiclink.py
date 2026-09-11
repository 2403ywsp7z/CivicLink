"""Initial CivicLink schema — generated from SQLAlchemy metadata.

Revision ID: 0001_civiclink
"""

from alembic import op  # noqa: F401
from sqlalchemy.orm import Session  # noqa: F401

revision = "0001_civiclink"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models import entities  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.db.base import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
