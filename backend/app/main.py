"""FastAPI application entry point.

Run with: uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.core.errors import AppError, app_error_handler, unhandled_error_handler
from backend.app.core.logging import configure_logging, get_logger
from backend.app.infrastructure.storage import ensure_storage_dirs

configure_logging()
log = get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title="Meeting Intelligence API",
    version="0.1.0",
    description="Audio upload & timestamped transcription (v0.1).",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]

# Ensure storage directory exists
ensure_storage_dirs(settings.storage_root)

# Routes
from backend.app.api.v1.meetings import router as meetings_router

app.include_router(meetings_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}
