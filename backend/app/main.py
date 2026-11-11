from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.routers import (
    ack,
    cards,
    coach,
    health,
    incidents,
    places,
    public,
    reports,
    responder,
)
from app.utils.errors import ApiError, api_error_handler, validation_handler


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = None
    if settings.SIMULATION_ENABLED:  # F-26: ambulances move only in simulation mode
        from app.jobs import ambulance_sim

        scheduler = ambulance_sim.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Golden Minute", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_handler)

origins = [settings.FRONTEND_BASE_URL]
if settings.PUBLIC_BASE_URL:
    origins.append(settings.PUBLIC_BASE_URL)
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"]
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(ack.router, prefix="/api/v1")
app.include_router(cards.router, prefix="/api/v1")
app.include_router(places.router, prefix="/api/v1")
app.include_router(coach.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(responder.router, prefix="/api/v1")

if settings.TELEGRAM_ENABLED:  # optional channel, off by default
    from app.routers import webhooks_telegram

    app.include_router(webhooks_telegram.router)
