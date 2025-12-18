from __future__ import annotations

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None


class LoginURLResponse(BaseModel):
    authorization_url: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
