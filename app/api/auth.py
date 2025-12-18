from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, generate_refresh_token, hash_token
from app.models.oauth_state import OAuthState
from app.models.player import Player
from app.models.session import Session
from app.schemas.auth import LoginURLResponse, RefreshTokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_authorize_url(state: str) -> str:
    if not settings.discord_client_id or not settings.discord_redirect_uri:
        raise HTTPException(status_code=500, detail="Discord OAuth 未設定")
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"


async def _create_oauth_state(db: AsyncSession) -> str:
    """Create and store a new OAuth state token in the database."""
    state = secrets.token_urlsafe(32)
    oauth_state = OAuthState(
        state=state,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),  # 5 minute expiry
        used=False,
    )
    db.add(oauth_state)
    await db.commit()
    logger.debug(f"Created OAuth state: {state}")
    return state


async def _validate_and_consume_state(db: AsyncSession, state: str) -> bool:
    """Validate and mark an OAuth state as used.

    Returns True if valid, False otherwise.
    """
    result = await db.exec(
        select(OAuthState).where(
            OAuthState.state == state,
            OAuthState.used == False,  # noqa: E712
            OAuthState.expires_at > datetime.now(UTC),
        )
    )
    oauth_state = result.first()

    if not oauth_state:
        logger.warning(f"Invalid or expired OAuth state: {state}")
        return False

    # Mark as used to prevent replay attacks
    oauth_state.used = True
    await db.commit()
    logger.debug(f"Validated and consumed OAuth state: {state}")
    return True


@router.get("/discord/login")
async def discord_login(db: Annotated[AsyncSession, Depends(get_db)]) -> LoginURLResponse:
    """Generate a Discord OAuth authorization URL with a secure state token stored in DB."""
    state = await _create_oauth_state(db)
    url = _build_authorize_url(state)
    return LoginURLResponse(authorization_url=url)


@router.get("/discord/callback")
async def discord_callback(
    code: str, state: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    # Validate state from database
    is_valid = await _validate_and_consume_state(db, state)
    if not is_valid:
        raise HTTPException(status_code=400, detail="無效或已過期的 OAuth 狀態 Token")

    if not (
        settings.discord_client_id
        and settings.discord_client_secret
        and settings.discord_redirect_uri
    ):
        raise HTTPException(status_code=500, detail="Discord OAuth 未設定")

    data = {
        "client_id": settings.discord_client_id,
        "client_secret": settings.discord_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.discord_redirect_uri,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            logger.error(
                f"Discord token exchange failed: {token_resp.status_code} {token_resp.text}"
            )
            raise HTTPException(status_code=400, detail="Token 交換失敗")
        token_json = token_resp.json()
        discord_access = token_json.get("access_token")
        if not discord_access:
            raise HTTPException(status_code=400, detail="Discord 未提供存取 Token")

        me_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {discord_access}"},
        )
        if me_resp.status_code != 200:
            logger.error(f"Discord /users/@me failed: {me_resp.status_code} {me_resp.text}")
            raise HTTPException(status_code=400, detail="無法取得 Discord 使用者資訊")
        me = me_resp.json()

    try:
        discord_user_id = int(me["id"])  # BigInteger
    except Exception:
        raise HTTPException(status_code=400, detail="無效的 Discord 使用者 ID") from None

    # Extract Discord username
    discord_username = me.get("username") or me.get("global_name")

    # Upsert player
    result = await db.exec(select(Player).where(Player.id == discord_user_id))
    player = result.first()
    if not player:
        player = Player(id=discord_user_id, name=discord_username, is_admin=False)
        db.add(player)
        await db.commit()
        await db.refresh(player)
    # Update name if it changed
    elif discord_username and player.name != discord_username:
        player.name = discord_username
        await db.commit()
        await db.refresh(player)

    # Create (or reuse) a session row and refresh token
    refresh_token = generate_refresh_token()
    token_hash = hash_token(refresh_token)
    session = Session(
        player_id=player.id,
        token_hash=token_hash,
        revoked=False,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Access token
    access = create_access_token(sub=str(player.id), is_admin=player.is_admin, sid=session.id)

    # Return tokens in response body
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.post("/refresh")
async def refresh_token_endpoint(
    body: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    raw_refresh = body.refresh_token
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="缺少重新整理 Token")

    token_hash = hash_token(raw_refresh)
    result = await db.exec(
        select(Session).where(Session.token_hash == token_hash, Session.revoked == False)  # noqa: E712
    )
    session = result.first()
    if not session or session.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="無效或已過期的重新整理 Token")

    # Rotate refresh token: update token_hash and expiry
    new_refresh = generate_refresh_token()
    session.token_hash = hash_token(new_refresh)
    session.expires_at = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds)
    await db.commit()
    await db.refresh(session)

    # Re-issue access token
    # Fetch player to read is_admin
    result = await db.exec(select(Player).where(Player.id == session.player_id))
    player = result.first()
    if not player:
        raise HTTPException(status_code=404, detail="找不到使用者")

    access = create_access_token(sub=str(player.id), is_admin=player.is_admin, sid=session.id)

    # Return tokens in response body
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    body: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, str]:
    raw_refresh = body.refresh_token
    if raw_refresh:
        token_hash = hash_token(raw_refresh)
        result = await db.exec(select(Session).where(Session.token_hash == token_hash))
        session = result.first()
        if session:
            session.revoked = True
            await db.commit()

    return {"message": "Logged out"}
