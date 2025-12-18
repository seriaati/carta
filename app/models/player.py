import sqlmodel
from pydantic import field_serializer

from ._base import BaseModel


class Player(BaseModel, table=True):
    __tablename__: str = "players"

    id: int = sqlmodel.Field(
        primary_key=True,
        index=True,
        sa_type=sqlmodel.BigInteger,
        sa_column_kwargs={"autoincrement": False},
    )
    """Discord user ID"""
    name: str | None = sqlmodel.Field(default=None, nullable=True)
    """Discord username"""
    is_admin: bool = False
    currency: int = sqlmodel.Field(default=0, ge=0)

    @field_serializer("id")
    def serialize_id(self, value: int) -> str:
        """Serialize ID as string for JavaScript compatibility with large Discord IDs."""
        return str(value)
