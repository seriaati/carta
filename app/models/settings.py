import sqlmodel

from ._base import BaseModel


class Settings(BaseModel, table=True):
    __tablename__: str = "settings"

    key: str = sqlmodel.Field(primary_key=True, index=True)
    value: str
