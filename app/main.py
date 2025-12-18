from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine
from app.utils.exception_handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.utils.router_discovery import register_routers


@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncGenerator[None, FastAPI]:
    yield

    await engine.dispose()


app = FastAPI(
    title="Card Game API",
    lifespan=app_lifespan,
    servers=[{"url": "http://localhost:8080", "description": "Local server"}],
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


register_routers(app)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def healthz() -> str:
    return "OK"
