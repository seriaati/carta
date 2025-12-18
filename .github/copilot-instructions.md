# Copilot Coding Agent Instructions for card-game

## Project Overview

This is a **FastAPI-based card game backend API** with PostgreSQL database, supporting card battle mechanics, player management, PvP challenges, trading, and shop systems. The project is written in **Python 3.13** and uses modern async patterns.

**Repository Stats:**
- **Type:** FastAPI REST API backend
- **Primary Language:** Python 3.13
- **Framework:** FastAPI + SQLModel (SQLAlchemy ORM)
- **Database:** PostgreSQL with asyncpg driver
- **Package Manager:** UV (modern Python package manager)
- **Lines of Code:** ~2000+ lines across 68 Python files
- **Main Dependencies:** FastAPI, SQLModel, Alembic, Discord.py, OpenAI, Loguru

## Critical: Environment Setup Requirements

### 1. Python Environment & Dependencies

**ALWAYS run these commands in order before any other operations:**

```powershell
# Install dependencies (REQUIRED first step for any work)
uv sync
```

**Important:** UV automatically creates and manages a virtual environment in `.venv/`. All commands should be run with `uv run` prefix to use the correct environment.

### 2. Required Environment Variables

**CRITICAL:** Create a `.env` file in the project root with these required variables:

```env
DB_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
OPENAI_API_KEY=sk-...
CDN_URL=https://your-cdn-url.com
CDN_API_KEY=your-cdn-api-key

# Optional OAuth settings
DISCORD_CLIENT_ID=your-discord-client-id
DISCORD_CLIENT_SECRET=your-discord-client-secret
DISCORD_REDIRECT_URI=http://localhost:8080/api/auth/discord/callback

# Optional JWT settings (ephemeral secret generated if not set)
JWT_SECRET=your-secret-key-here
```

**Without a valid `.env` file, the application CANNOT start.** The DB_URL must point to a running PostgreSQL instance.

## Build, Lint, Format & Run Commands

### Validation Workflow (Run in this exact order)

**1. Install Dependencies:**
```powershell
uv sync
```
- **Duration:** 1-3 seconds (if already cached)
- **ALWAYS run this first** before any other command
- **Failure mode:** None - creates lockfile if missing

**2. Format Code:**
```powershell
uv run ruff format
```
- **Duration:** 1-2 seconds
- **ALWAYS run before linting** to auto-fix formatting issues
- Formats all Python files according to `ruff.toml` configuration
- **Never fails** - always succeeds by formatting files

**3. Lint Code:**
```powershell
uv run ruff check --fix
```
- **Duration:** 1-2 seconds
- Auto-fixes many issues (imports, whitespace, etc.)
- Use `--unsafe-fixes` flag for additional auto-fixes on docstring whitespace issues
- **Exit code 1** means there are unfixed linting issues that need manual attention
- **Known issue:** Blank lines with whitespace in docstrings may require `--unsafe-fixes` or manual fixing

**4. Type Check:**
```powershell
uv run pyright
```
- **Note:** Pyright configuration exists in `pyproject.toml` but the tool itself is not a project dependency
- If type checking is needed, pyright must be installed separately (e.g., `npm install -g pyright`)

### Database Migration Commands

**CRITICAL:** All Alembic commands require a valid database connection (DB_URL in .env must point to an accessible PostgreSQL instance).

```powershell
# Create a new migration after model changes
uv run alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
uv run alembic upgrade head

# Check current migration version
uv run alembic current

# Downgrade one migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

**Migration workflow:**
1. Modify models in `app/models/`
2. Import new models in `app/models/__init__.py`
3. Run `uv run alembic revision --autogenerate -m "description"`
4. Review the generated migration in `alembic/versions/`
5. Run `uv run alembic upgrade head` to apply

**Common issues:**
- **"password authentication failed"** - DB_URL credentials are incorrect
- **"connection refused"** - PostgreSQL is not running or not accessible at specified host/port
- Alembic cannot run without a database connection, unlike the application import which can run with dummy env vars

## Project Structure & Architecture

### Directory Layout

```
card-game/
├── .env                          # Environment variables (REQUIRED, not in git)
├── .python-version               # Python 3.13
├── pyproject.toml                # Project metadata, dependencies, tool configs
├── ruff.toml                     # Linting/formatting rules
├── alembic.ini                   # Alembic migration configuration
├── run.py                        # Application entry point
├── uv.lock                       # Dependency lockfile
├── alembic/
│   ├── env.py                    # Alembic environment setup
│   └── versions/                 # Database migration files (auto-generated)
│       ├── 2025_11_07_1021-96d4cba3197c_initial_scheme.py
│       ├── 2025_11_07_1146-63da4a59e519_security.py
│       └── 2025_11_22_1031-9db981b29d9f_change_image_to_url.py
├── app/
│   ├── main.py                   # FastAPI app initialization, CORS, router registration
│   ├── api/                      # API route handlers (13 modules)
│   │   ├── auth.py               # Discord OAuth & JWT authentication
│   │   ├── card.py               # Card CRUD operations
│   │   ├── player.py             # Player management
│   │   ├── inventory.py          # Player card inventory
│   │   ├── deck_card.py          # Player deck management
│   │   ├── card_pool.py          # Gacha/card pool system
│   │   ├── card_pool_card.py     # Card pool associations
│   │   ├── shop_item.py          # In-game shop
│   │   ├── trade.py              # Player-to-player trading
│   │   ├── pvp_challenge.py      # PvP challenge system
│   │   ├── pvp_rank.py           # PvP ranking system
│   │   ├── event_log.py          # Event logging/history
│   │   └── settings.py           # Player settings
│   ├── core/                     # Core configuration & infrastructure
│   │   ├── config.py             # Pydantic settings (loads from .env)
│   │   ├── db.py                 # Database engine & session dependency
│   │   ├── security.py           # JWT creation/validation, auth dependencies
│   │   └── enums.py              # Shared enums (Rarity, TradeStatus, etc.)
│   ├── models/                   # SQLModel database models (14 models)
│   │   ├── __init__.py           # REQUIRED: imports all models for Alembic
│   │   ├── _base.py              # BaseModel with created_at/updated_at
│   │   ├── card.py               # Card model
│   │   ├── player.py             # Player model
│   │   ├── session.py            # User session model (auth)
│   │   └── ...                   # Other domain models
│   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── common.py             # APIResponse, PaginatedResponse, PaginationData
│   │   ├── card.py               # CardCreate, CardUpdate
│   │   └── ...                   # Schemas matching each API module
│   ├── services/                 # Business logic layer (12 service classes)
│   │   ├── card.py               # CardService (CRUD + CDN image upload)
│   │   └── ...                   # Service classes matching API modules
│   └── utils/
│       ├── router_discovery.py   # Automatic FastAPI router registration
│       ├── logging.py            # Loguru configuration
│       ├── cdn.py                # Image upload to CDN utility
│       └── misc.py               # Miscellaneous utilities
└── logs/
    └── application.log           # Auto-created by Loguru (rotates at 50MB)
```

### Architectural Patterns

**1. Layered Architecture:**
- **API Layer** (`app/api/*.py`): Route handlers, request validation
- **Service Layer** (`app/services/*.py`): Business logic, database operations
- **Model Layer** (`app/models/*.py`): SQLModel ORM models
- **Schema Layer** (`app/schemas/*.py`): Pydantic request/response validation

**2. Dependency Injection:**
- Database sessions injected via `Depends(get_db)`
- Services automatically instantiated with `Depends()` in route handlers
- Auth dependencies in `app/core/security.py` for protected routes

**3. Router Auto-Discovery:**
- All routers in `app/api/*.py` are automatically discovered and registered
- Router discovery happens in `app/utils/router_discovery.py`
- Each API module exports a `router = APIRouter(prefix="/resource", tags=["resource"])`
- No manual router registration needed in `main.py`

**4. Database Models:**
- All models inherit from `BaseModel` (in `app/models/_base.py`)
- `BaseModel` provides automatic `created_at` and `updated_at` timestamps
- Models use SQLModel (combination of SQLAlchemy + Pydantic)
- **CRITICAL:** New models MUST be imported in `app/models/__init__.py` for Alembic autogenerate

**5. Image Handling:**
- Card images sent as raw bytes from frontend
- `app/utils/cdn.py` converts bytes to base64 data URI
- Uploads to external CDN via HTTP POST
- Stores returned CDN URL in database (not bytes)

## Code Style & Linting Rules

### Ruff Configuration (ruff.toml)

**Settings:**
- Line length: 100 characters
- Target: Python 3.13
- Very strict rule set enabled (see `select` array in ruff.toml)

**Key Rules Ignored:**
- `S101`: Assert statements allowed
- `PLR2004`: Magic values allowed
- `PLR6301`: Method could be static/classmethod warnings ignored
- `ANN401`: `typing.Any` allowed
- `E501`: Line length not enforced (formatter handles it)
- `DTZ007`: Naive datetime construction allowed

**Per-File Ignores:**
- `**/__init__.py`: F403, F401 (wildcard imports allowed)
- `alembic/versions/*.py`: ALL (migration files exempt)

**Import Sorting:**
- Uses isort-compatible rules
- No trailing comma splitting

**Type Checking:**
- Runtime-evaluated base classes: `pydantic.BaseModel`, `pydantic_settings.BaseSettings`
- Enables quote-annotations for forward references

### Common Code Patterns

**1. API Route Handler:**
```python
from typing import Annotated
from fastapi import APIRouter, Depends
from app.services.resource import ResourceService

router = APIRouter(prefix="/resources", tags=["resources"])

@router.get("/{id}")
async def get_resource(
    id: int,
    service: Annotated[ResourceService, Depends()]
) -> APIResponse[Resource]:
    resource = await service.get_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Not found")
    return APIResponse(data=resource)
```

**2. Service Class:**
```python
from typing import Annotated
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.db import get_db

class ResourceService:
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db

    async def get_resource(self, id: int) -> Resource | None:
        result = await self.db.exec(select(Resource).where(Resource.id == id))
        return result.first()
```

**3. Model Definition:**
```python
import sqlmodel
from app.models._base import BaseModel

class Resource(BaseModel, table=True):
    __tablename__: str = "resources"

    id: int = sqlmodel.Field(primary_key=True, index=True, default=None)
    name: str = sqlmodel.Field(max_length=100, index=True)
    # Add other fields...
```

## Testing

**Status:** No test suite currently exists.
- `tests` directory mentioned in pyproject.toml but not present
- No pytest dependency installed
- `.pytest_cache/` in .gitignore suggests tests were planned

**For adding tests:**
1. Add `pytest` and `pytest-asyncio` to dependencies
2. Create `tests/` directory
3. Follow async testing patterns for FastAPI
4. Use `AsyncClient` for API testing

## Common Issues & Workarounds

### 1. Ruff Docstring Whitespace Warnings
**Issue:** `W293 Blank line contains whitespace` in docstrings
**Solution:** Run `uv run ruff check --fix --unsafe-fixes` or manually remove whitespace from blank lines in docstrings

### 2. Database Connection Errors
**Issue:** Alembic or application fails with connection errors
**Solution:** Verify `.env` file has correct `DB_URL` with valid credentials and accessible PostgreSQL server

### 3. Import Errors After Adding Models
**Issue:** New model not detected by Alembic autogenerate
**Solution:** Add import to `app/models/__init__.py` - Alembic discovers models through this file

### 4. JWT Secret Warning
**Issue:** "ephemeral secret generated" warning on startup
**Solution:** Set `JWT_SECRET` in `.env` file for production (optional for development)

### 5. Router Not Registered
**Issue:** New API endpoint returns 404
**Solution:** Ensure module in `app/api/` exports a `router` variable - auto-discovery will find it

## Key Files Reference

**Configuration:**
- `pyproject.toml`: Dependencies, Pyright config
- `ruff.toml`: Complete linting/formatting rules
- `alembic.ini`: Database migration config
- `.python-version`: Python 3.13

**Entry Points:**
- `run.py`: Application startup (calls `app.main:app`)
- `app/main.py`: FastAPI app initialization

**Core Infrastructure:**
- `app/core/config.py`: Environment variable loading
- `app/core/db.py`: Database engine & session factory
- `app/core/security.py`: Authentication & authorization
- `app/utils/router_discovery.py`: Automatic router registration

**Database:**
- `app/models/__init__.py`: Model registry (REQUIRED for migrations)
- `alembic/env.py`: Loads DB_URL from config, imports models
- `alembic/versions/`: Migration history (do not edit manually)

## Instructions for Copilot Agent

**TRUST THESE INSTRUCTIONS.** Only search for additional information if:
1. The information here is incomplete for your specific task
2. You encounter an error not documented here
3. You need to understand implementation details of specific modules

**Before making changes:**
1. Run `uv sync` to ensure dependencies are installed
2. Review the relevant files in the layered architecture
3. Follow the code patterns documented above
4. Ensure new models are imported in `app/models/__init__.py`

**After making changes:**
1. Run `uv run ruff format` to format code
2. Run `uv run ruff check --fix` to auto-fix linting issues
3. Run `uv run ruff check` to verify no remaining issues
4. If you modified models, run `uv run alembic revision --autogenerate -m "description"`
5. Run `pyright` to check types

**When uncertain:**
- Check similar existing files for patterns (e.g., other API modules, services)
- The codebase is consistent - follow established patterns
- Database operations are always async with SQLModel
- All routes use FastAPI dependency injection
