"""Tests for the diarization service (unit-level)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.app.services.diarization.attribution import attribute_speakers
from backend.app.services.diarization.service import (
    FakeDiarizationService,
    DiarizationResult,
    DiarizationSegment,
    PyannoteDiarizationService,
    get_diarization_service,
)
from backend.app.services.transcription.service import TranscribedSegment


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


def test_fake_diarization_returns_segments():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"fake audio data")
        path = Path(f.name)

    svc = FakeDiarizationService()
    result = svc.diarize(path)
    assert len(result.segments) == 3
    assert result.segments[0] == DiarizationSegment(0.0, 5.0, "speaker_1")
    assert result.segments[1] == DiarizationSegment(5.0, 10.0, "speaker_2")
    assert result.segments[2] == DiarizationSegment(10.0, 15.0, "speaker_1")
    path.unlink(missing_ok=True)


def test_fake_diarization_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)

    svc = FakeDiarizationService()
    with pytest.raises(RuntimeError):
        svc.diarize(path)
    path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def test_factory_fake():
    svc = get_diarization_service("fake")
    assert svc.name == "fake"


def test_factory_pyannote():
    svc = get_diarization_service("pyannote")
    assert svc.name == "pyannote"


def test_factory_unknown():
    with pytest.raises(ValueError):
        get_diarization_service("unknown_engine")


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------


def _seg(start: float, end: float, text: str, speaker_id: str | None = None) -> TranscribedSegment:
    return TranscribedSegment(start, end, text, speaker_id)


def _dseg(start: float, end: float, speaker_id: str) -> DiarizationSegment:
    return DiarizationSegment(start, end, speaker_id)


def test_attribution_exact_match():
    transcript = [
        _seg(0.5, 4.0, "Hello"),
        _seg(5.5, 9.0, "I agree"),
        _seg(10.5, 14.0, "Let's discuss"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 10.0, "speaker_2"),
        _dseg(10.0, 15.0, "speaker_1"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id == "speaker_1"
    assert result[1].speaker_id == "speaker_2"
    assert result[2].speaker_id == "speaker_1"


def test_attribution_exact_boundary():
    transcript = [
        _seg(5.0, 9.0, "Boundary test"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 10.0, "speaker_2"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id == "speaker_2"


def test_attribution_partial_overlap():
    transcript = [
        _seg(1.0, 4.0, "Partial"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 10.0, "speaker_2"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id == "speaker_1"


def test_attribution_no_match():
    transcript = [
        _seg(20.0, 25.0, "Orphan"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 10.0, "speaker_2"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id is None


def test_attribution_multiple_overlapping_candidates():
    transcript = [
        _seg(4.0, 6.0, "Overlap zone"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 10.0, "speaker_2"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id == "speaker_1"


def test_attribution_long_transcript_segment():
    transcript = [
        _seg(0.0, 15.0, "Long segment spanning all"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 10.0, "speaker_2"),
        _dseg(10.0, 15.0, "speaker_1"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id == "speaker_1"


def test_attribution_single_speaker():
    transcript = [
        _seg(0.0, 3.0, "A"),
        _seg(3.0, 7.0, "B"),
        _seg(7.0, 10.0, "C"),
    ]
    diarization = [
        _dseg(0.0, 10.0, "speaker_1"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert all(s.speaker_id == "speaker_1" for s in result)


def test_attribution_multiple_speakers():
    transcript = [
        _seg(0.0, 4.0, "A"),
        _seg(4.5, 8.0, "B"),
        _seg(8.5, 12.0, "C"),
    ]
    diarization = [
        _dseg(0.0, 5.0, "speaker_1"),
        _dseg(5.0, 9.0, "speaker_2"),
        _dseg(9.0, 13.0, "speaker_1"),
    ]
    result = attribute_speakers(transcript, diarization)
    assert result[0].speaker_id == "speaker_1"
    assert result[1].speaker_id == "speaker_2"
    assert result[2].speaker_id == "speaker_1"


def test_attribution_empty_diarization():
    transcript = [_seg(0.0, 1.0, "Hello")]
    result = attribute_speakers(transcript, [])
    assert result[0].speaker_id is None
