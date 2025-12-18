from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.player import Player

# HTTP Bearer scheme for FastAPI dependencies
bearer_scheme = HTTPBearer(auto_error=False)


def _get_jwt_secret() -> str:
    """Get the JWT secret, generating an ephemeral one for dev if not set.

    WARNING: If not set, an ephemeral secret is generated per-process, which will
    invalidate tokens on restart. Configure settings.jwt_secret in production.
    """
    if settings.jwt_secret:
        return settings.jwt_secret
    # Ephemeral secret for development; log a warning
    secret = secrets.token_urlsafe(32)
    logger.warning(
        "JWT secret not configured. Using ephemeral secret for this process; tokens will invalidate on restart."
    )
    # Cache on settings to keep it stable during process lifetime
    settings.jwt_secret = secret
    return secret


def create_access_token(*, sub: str, is_admin: bool, sid: int | None = None) -> str:
    """Create a short-lived access JWT.

    Claims:
      - sub: subject (discord user id as string)
      - is_admin: bool
      - sid: session id (optional)
      - exp: expiry
      - iat: issued at
    """
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=settings.access_token_ttl_seconds)
    payload: dict[str, Any] = {
        "sub": sub,
        "is_admin": is_admin,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if sid is not None:
        payload["sid"] = sid
    return jwt.encode(payload, _get_jwt_secret(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token, returning claims or raising.

    Raises jwt.InvalidTokenError (caught by caller) on invalid token.
    """
    return jwt.decode(token, _get_jwt_secret(), algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token string."""
    # ~86 chars URL-safe, 64+ bytes entropy
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_current_player(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Player:
    """Resolve the current Player from Authorization: Bearer <jwt>.

    - 401 if missing/invalid
    - 404 if user not found (e.g., deleted)
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="未驗證")
    token = credentials.credentials
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已過期") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="無效的 Token") from None

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="無效的 Token 內容")

    # sub is discord user id; DB column is BigInteger
    try:
        player_id = int(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="無效的主體") from None

    result = await db.exec(select(Player).where(Player.id == player_id))
    player = result.first()
    if not player:
        raise HTTPException(status_code=404, detail="找不到使用者")
    return player


def require_admin(player: Annotated[Player, Depends(get_current_player)]) -> Player:
    if not player.is_admin:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return player


def get_client_ip(request: Request) -> str | None:
    # Best-effort, depends on deployment proxy
    ip = request.headers.get("x-forwarded-for") or request.client.host if request.client else None
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    return ip
