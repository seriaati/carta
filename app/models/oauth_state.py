from __future__ import annotations

from datetime import datetime

import sqlmodel

from ._base import BaseModel


class OAuthState(BaseModel, table=True):
    """OAuth state tokens for CSRF protection during OAuth flows."""

    __tablename__: str = "oauth_states"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    state: str = sqlmodel.Field(max_length=255, index=True, unique=True)
    expires_at: datetime = sqlmodel.Field(index=True, sa_type=sqlmodel.DateTime(timezone=True))
    used: bool = sqlmodel.Field(default=False, index=True)
