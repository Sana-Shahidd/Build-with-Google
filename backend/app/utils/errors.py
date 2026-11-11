"""Error body for every non-2xx response (docs/06_API_SPEC.md §1)."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=body(exc.code, exc.message))


async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    return JSONResponse(
        status_code=400,
        content=body("VALIDATION_ERROR", f"{loc}: {first.get('msg', 'invalid')}"),
    )
