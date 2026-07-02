from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from api.routes.analysis import router as analysis_router
from api.routes.health import router as health_router
from api.routes.profiles import router as profiles_router
from config import get_settings

# ---- Logging Setup ----
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create required directories on startup."""
    settings = get_settings()
    for directory in (
        settings.storage_dir,
        settings.uploads_dir,
        settings.profiles_dir,
        settings.analyses_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    logger.info("Climb Beta Solver API starting", version=settings.app_version)
    yield
    logger.info("Climb Beta Solver API shutting down")


app = FastAPI(
    title="Climb Beta Solver API",
    description="AI-powered bouldering beta solver with computer vision and biomechanics",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Exception Handlers ----
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning("Validation error", path=str(request.url), errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": "Validation failed"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", path=str(request.url), exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please check server logs."},
    )


# ---- Routers ----
app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(profiles_router)

# ---- Static Files (uploaded images) ----
uploads_path = settings.uploads_dir
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.get("/")
async def root() -> dict:
    return {
        "name": "Climb Beta Solver API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
