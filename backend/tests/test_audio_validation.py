"""Tests for audio validation service (unit-level)."""

from __future__ import annotations

import io

import pytest
from starlette.datastructures import UploadFile, Headers

from backend.app.core.errors import AppError
from backend.app.services.audio_validation import validate_audio_upload


def _upload(filename: str, content: bytes = b"fake", mime: str = "audio/wav") -> UploadFile:
    headers = Headers({"content-type": mime})
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=headers)


def test_valid_wav():
    u = _upload("clip.wav")
    ext = validate_audio_upload(u, max_size_bytes=10_000_000, declared_size=100)
    assert ext == ".wav"


def test_valid_mp3():
    u = _upload("song.mp3", mime="audio/mpeg")
    ext = validate_audio_upload(u, max_size_bytes=10_000_000, declared_size=100)
    assert ext == ".mp3"


def test_valid_m4a():
    u = _upload("rec.m4a", mime="audio/mp4")
    ext = validate_audio_upload(u, max_size_bytes=10_000_000, declared_size=100)
    assert ext == ".m4a"


def test_unsupported_extension():
    u = _upload("doc.pdf", mime="application/pdf")
    with pytest.raises(AppError) as exc_info:
        validate_audio_upload(u, max_size_bytes=10_000_000, declared_size=100)
    assert exc_info.value.code == "INVALID_AUDIO_FILE"


def test_empty_upload():
    with pytest.raises(AppError) as exc_info:
        validate_audio_upload(None, max_size_bytes=10_000_000)
    assert exc_info.value.code == "EMPTY_UPLOAD"


def test_file_too_large():
    u = _upload("big.wav")
    with pytest.raises(AppError) as exc_info:
        validate_audio_upload(u, max_size_bytes=1000, declared_size=2000)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_zero_size_file():
    u = _upload("zero.wav")
    with pytest.raises(AppError) as exc_info:
        validate_audio_upload(u, max_size_bytes=10_000_000, declared_size=0)
    assert exc_info.value.code == "EMPTY_UPLOAD"
