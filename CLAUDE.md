# Card Game Project - AI Agent Guide

A Discord-integrated card game with FastAPI backend and dual Discord bot/web interfaces.

## Project Architecture

### Two Independent Services

1. **FastAPI Backend** (`app/`): RESTful API with PostgreSQL via SQLModel/SQLAlchemy
2. **Discord Bot** (`bot/`): Discord.py client consuming the API

**Critical**: Both services share the database engine (`app.core.db.engine`) but NOT the database session. Bot uses `bot.utils.db.get_session()` (unmanaged), API uses `app.core.db.get_db()` (dependency-injected, auto-managed).

### Core Data Flow Pattern

```
Discord User → OAuth → FastAPI creates Player → JWT tokens → Bot/Web requests
```

## Key Architectural Decisions

### Authentication & Authorization

- **OAuth Flow**: Discord OAuth2 with CSRF state tokens stored in DB (`OAuthState` model)
- **JWT + Refresh Tokens**: Access tokens (15min) + refresh tokens (30d) stored as hashed `Session` records
- **Admin System**: `Player.is_admin` flag gates admin endpoints via `require_admin` dependency
- **Security**: See [app/core/security.py](app/core/security.py) for JWT handling, [app/api/auth.py](app/api/auth.py) for OAuth flow

### Database Schema Pattern

All models inherit from [app/models/_base.py](app/models/_base.py):

```python
class BaseModel(sqlmodel.SQLModel):
    created_at: datetime  # auto server_default=now()
    updated_at: datetime  # auto onupdate=now()
```

**Important**: Default values set to `None` with `sa_column_kwargs` to prevent SQLAlchemy errors (see discussion link in code).

### Router Auto-Discovery

[app/utils/router_discovery.py](app/utils/router_discovery.py) scans `app/api/*.py` for `APIRouter` instances and registers them with `/api` prefix. No manual router registration in `main.py` needed.

**Add new endpoint**: Create file in `app/api/`, define router with `APIRouter()`, restart server.

### Service Layer Pattern

- **Services** (`app/services/`): Business logic, DB transactions, cross-entity operations
- **API Routes** (`app/api/`): HTTP request/response, dependency injection, validation
- **Models** (`app/models/`): SQLModel tables (single source for DB + Pydantic schemas)
- **Schemas** (`app/schemas/`): Request/response DTOs when model fields differ from API surface

Example: [app/services/player.py](app/services/player.py) handles currency transactions + event logging, [app/api/player.py](app/api/player.py) handles HTTP routing.

## Critical Workflows

### Database Migrations (Alembic)

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

**Important**:

- Enum changes require `alembic-postgresql-enum` (already in deps)
- Migration files in `alembic/versions/` are excluded from linting
- Always review auto-generated migrations before applying

### Adding Currency Operations

See [app/api/ADMIN_CURRENCY_ENDPOINTS.md](app/api/ADMIN_CURRENCY_ENDPOINTS.md) for complete admin currency API reference.

Pattern for new transactional operations:

1. Add method to service (e.g., `PlayerService.increase_currency`)
2. Log event to `EventLog` with appropriate `EventType` enum
3. Wrap in single DB commit
4. Add admin-gated route in API layer

### Event Logging Pattern

All significant actions log to [app/models/event_log.py](app/models/event_log.py):

```python
EventLog(player_id=id, event_type=EventType.EARN_MONEY, context={"amount": 100, "reason": "..."})
```

**Context field**: JSON/dict for flexible structured data. See [app/core/enums.py](app/core/enums.py) for all event types.

## Development Practices

### Code Quality (Ruff)

[ruff.toml](ruff.toml) enforces strict linting (line-length 100, complexity ≤15):

```bash
ruff check app/ bot/  # Lint
ruff format app/ bot/ # Format
```

**Key ignores**:

- `S101`: Asserts allowed
- `E501`: Line length (handled by formatter)
- `ANN401`: `typing.Any` allowed
- Per-file: `__init__.py` allows wildcard imports, `alembic/versions/*.py` no linting

### Type Checking (Pyright)

[pyproject.toml](pyproject.toml) sets `standard` mode:

- All includes: `app/`, `bot/`, `run.py`, `tests/`
- Excludes: `alembic/versions/`
- Unnecessary ignore comments flagged
- Run with `uv run pyright`

### Async Patterns

- **FastAPI**: Native async with `async def` handlers
- **Database**: All DB ops use `await` with `AsyncSession`
- **Discord Bot**: Discord.py v2+ async API
- **HTTPx**: Used instead of requests for async HTTP calls (see OAuth flow)

### Configuration

[app/core/config.py](app/core/config.py) loads from `.env`:

- **Required**: `db_url`, `discord_*`, `cdn_api_key`, `openai_api_key`
- **Dev Mode**: Set `env=dev` to disable certain security features
- **JWT Secret**: Ephemeral if not set (logs warning, tokens invalidate on restart)

## Common Tasks

### Add New API Endpoint

1. Create router in `app/api/new_feature.py`
2. Add service in `app/services/new_feature.py` (if business logic needed)
3. Define schemas in `app/schemas/new_feature.py` (if request/response DTOs needed)
4. Router auto-registered at `/api/new-feature`

### Add Database Model

1. Create model in `app/models/new_table.py` inheriting `BaseModel`
2. Generate migration: `alembic revision --autogenerate -m "add new_table"`
3. Review + edit migration in `alembic/versions/`
4. Apply: `alembic upgrade head`

### Add Discord Command

1. Create cog in `bot/cogs/feature.py`
2. Auto-loaded by `bot/main.py` during `setup_hook()`
3. Access DB via `bot.utils.db.get_session()` (remember to close session)
4. Use `httpx` to call FastAPI endpoints if needed

## Testing & Debugging

### Running Services

```bash
# FastAPI (port 8080)
uvicorn app.main:app --reload --port 8080

# Discord Bot
python -m bot.main  # or run.py if it exists
```

### Database Access

Direct access via `asyncpg` connection string from `settings.db_url`. Use tool like pgAdmin or psql CLI.

### Common Issues

- **"Player not found" after OAuth**: Check `Player.id` matches Discord user ID (BigInteger)
- **Session expiry errors**: Refresh token may have expired or been revoked (check `Session.revoked`)
- **Router not found**: Ensure router variable name is `router` in API file
- **Migration conflicts**: Check `alembic_version` table, may need manual intervention

## File Structure Reference

```
app/
├── api/          # HTTP routes (auto-discovered)
├── core/         # Config, DB, security, enums
├── models/       # SQLModel database tables
├── schemas/      # Pydantic DTOs
├── services/     # Business logic layer
└── utils/        # Helpers (router discovery, exceptions)

bot/
├── cogs/         # Discord commands (auto-loaded)
├── ui/           # Discord UI components
└── utils/        # Bot-specific helpers

alembic/
└── versions/     # Database migrations
```

## Enums & Constants

[app/core/enums.py](app/core/enums.py) defines:

- `CardRarity`: C, R, SR, SSR, UR, LR, EX
- `EventType`: All loggable events (money, cards, admin actions)
- `TradeStatus` / `PvPStatus`: Transaction states
- `CardSortField` / `SortOrder`: Query sorting options

## Security Notes

- **Admin operations**: All currency/data manipulation requires `require_admin`
- **CSRF protection**: OAuth state tokens prevent authorization code injection
- **Refresh token rotation**: New token issued on each refresh, old one invalidated
- **JWT expiry**: Short-lived access tokens (15min), long-lived refresh (30d)
- **Password-free**: Uses Discord OAuth exclusively (no password storage)
