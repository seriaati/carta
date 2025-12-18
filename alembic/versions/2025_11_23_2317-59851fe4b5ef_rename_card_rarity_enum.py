# pyright: reportAttributeAccessIssue=false, reportUndefinedVariable=false
"""Rename card rarity enum

Revision ID: 59851fe4b5ef
Revises: ed81bedc7a02
Create Date: 2025-11-23 23:17:17.239156

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "59851fe4b5ef"
down_revision: str | None = "ed81bedc7a02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert column to text temporarily
    op.execute("ALTER TABLE cards ALTER COLUMN rarity TYPE TEXT")

    # Drop the old enum
    sa.Enum("C", "R", "SR", "SSR", "UR", "LR", "EX", name="rarity").drop(op.get_bind())

    # Create the new enum
    sa.Enum("C", "R", "SR", "SSR", "UR", "LR", "EX", name="cardrarity").create(op.get_bind())

    # Convert column back to the new enum type
    op.execute("ALTER TABLE cards ALTER COLUMN rarity TYPE cardrarity USING rarity::cardrarity")


def downgrade() -> None:
    """Downgrade schema."""
    # Convert column to text temporarily
    op.execute("ALTER TABLE cards ALTER COLUMN rarity TYPE TEXT")

    # Drop the new enum
    sa.Enum("C", "R", "SR", "SSR", "UR", "LR", "EX", name="cardrarity").drop(op.get_bind())

    # Create the old enum
    sa.Enum("C", "R", "SR", "SSR", "UR", "LR", "EX", name="rarity").create(op.get_bind())

    # Convert column back to the old enum type
    op.execute("ALTER TABLE cards ALTER COLUMN rarity TYPE rarity USING rarity::rarity")
