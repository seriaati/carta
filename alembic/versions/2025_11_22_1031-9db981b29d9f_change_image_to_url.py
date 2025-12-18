# pyright: reportAttributeAccessIssue=false, reportUndefinedVariable=false
"""change_image_to_url

Revision ID: 9db981b29d9f
Revises: 63da4a59e519
Create Date: 2025-11-22 10:31:30.362716

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9db981b29d9f"
down_revision: str | None = "63da4a59e519"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change image column from LargeBinary to String (URL)
    op.alter_column(
        "cards", "image", type_=sa.String(), existing_type=sa.LargeBinary(), nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert image column from String back to LargeBinary
    op.alter_column(
        "cards", "image", type_=sa.LargeBinary(), existing_type=sa.String(), nullable=True
    )
