from datetime import datetime

import sqlmodel


class BaseModel(sqlmodel.SQLModel):
    # default is set to None, so it is not required when creating an instance of the model.
    # sa_type and sa_column_kwargs are used to prevent an error, see
    # https://github.com/fastapi/sqlmodel/discussions/743 for more info.

    created_at: datetime = sqlmodel.Field(
        default=None,
        sa_type=sqlmodel.DateTime(timezone=True),
        sa_column_kwargs={"server_default": sqlmodel.func.now()},
    )
    updated_at: datetime = sqlmodel.Field(
        default=None,
        sa_type=sqlmodel.DateTime(timezone=True),
        sa_column_kwargs={"onupdate": sqlmodel.func.now(), "server_default": sqlmodel.func.now()},
    )
