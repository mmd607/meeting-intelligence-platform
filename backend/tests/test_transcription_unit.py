"""Tests for the transcription service (unit-level)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.app.services.transcription.service import (
    FakeTranscriptionService,
    get_transcription_service,
)


def test_fake_transcription_returns_segments():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"fake audio data")
        path = Path(f.name)

    svc = FakeTranscriptionService()
    result = svc.transcribe(path)
    assert len(result.segments) > 0
    assert result.language == "en"
    assert result.duration_seconds is not None

    path.unlink(missing_ok=True)


def test_fake_transcription_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)

    svc = FakeTranscriptionService()
    with pytest.raises(RuntimeError):
        svc.transcribe(path)

    path.unlink(missing_ok=True)


def test_factory_fake():
    svc = get_transcription_service("fake")
    assert svc.name == "fake"


def test_factory_whisper():
    svc = get_transcription_service("whisper", "tiny")
    assert svc.name == "whisper"


def test_factory_unknown():
    with pytest.raises(ValueError):
        get_transcription_service("unknown_engine")
