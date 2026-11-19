"""Shared test fixtures."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.api.v1.meetings import get_db, router
from backend.app.infrastructure.db import Base
from backend.app.main import app


@pytest.fixture()
def tmp_storage(tmp_path: Path):
    """Provide a temporary storage root and patch settings."""
    return tmp_path / "storage"


@pytest.fixture()
def client(tmp_path: Path):
    """Fresh test client with an isolated SQLite DB + temp storage."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    session = TestSession()

    def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db

    # Patch storage to a temp dir
    from backend.app.core.config import get_settings, Settings

    settings = Settings(STORAGE_PATH=str(tmp_path / "storage"), DATABASE_URL=f"sqlite:///{db_path}")
    app.dependency_overrides[get_settings] = lambda: settings

    # Ensure storage dir exists
    from backend.app.infrastructure.storage import ensure_storage_dirs

    ensure_storage_dirs(settings.storage_root)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    session.close()


def _fake_audio_bytes() -> bytes:
    """Minimal valid WAV-like bytes for testing (header only)."""
    # RIFF header + fmt + data chunk — enough to pass extension check.
    return b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


def _make_upload_file(filename: str = "test.wav", content: bytes | None = None):
    """Create a Starlette UploadFile-like object for tests."""
    from starlette.datastructures import UploadFile

    data = content or _fake_audio_bytes()
    file_obj = io.BytesIO(data)
    return UploadFile(filename=filename, file=file_obj)
