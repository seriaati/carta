from typing import cast

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import APIResponse


def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    exc = cast(HTTPException, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(status="error", message=exc.detail).model_dump(),
    )


def validation_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    exc = cast(RequestValidationError, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(
            message="Validation error",
            data=[
                {"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()
            ],
        ).model_dump(),
    )


def general_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse(status="error", message=str(exc)).model_dump(),
    )
