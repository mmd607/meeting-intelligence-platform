"""Diarization abstraction (v0.2).

Application code depends only on DiarizationService; the concrete
engine (fake / pyannote) is chosen via config + factory.

Attribution is based on temporal overlap between transcript segments
and diarization segments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class DiarizationSegment:
    start_time: float
    end_time: float
    speaker_id: str


@dataclass
class DiarizationResult:
    segments: list[DiarizationSegment] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.segments is None:
            self.segments = []


class DiarizationService(ABC):
    name: str = "base"

    @abstractmethod
    def diarize(self, audio_path: Path) -> DiarizationResult:
        """Diarize audio file -> speaker-attributed segments. Raises on failure."""


class FakeDiarizationService(DiarizationService):
    """Deterministic stub for dev/tests. No external calls, no model."""

    name = "fake"

    def diarize(self, audio_path: Path) -> DiarizationResult:
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("Cannot diarize missing or empty audio file.")
        return DiarizationResult(
            segments=[
                DiarizationSegment(0.0, 5.0, "speaker_1"),
                DiarizationSegment(5.0, 10.0, "speaker_2"),
                DiarizationSegment(10.0, 15.0, "speaker_1"),
            ]
        )


class PyannoteDiarizationService(DiarizationService):
    """Pyannote-based diarization engine (lazy import).

    Requires: pip install pyannote.audio. Uses a pretrained segmentation
    and embedding model. This provider is isolated behind the abstraction;
    the rest of the app does not depend on pyannote.
    """

    name = "pyannote"

    def __init__(self) -> None:
        self._pipeline = None

    def _load_pipeline(self):
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "pyannote.audio is not installed. "
                    "Run `pip install pyannote.audio` or set DIARIZATION_PROVIDER=fake."
                ) from exc
            try:
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=False,
                )
            except Exception as exc:
                raise RuntimeError(
                    "Failed to load pyannote diarization pipeline. "
                    "Ensure the model is available and you accept the user agreement on Hugging Face."
                ) from exc
        return self._pipeline

    def diarize(self, audio_path: Path) -> DiarizationResult:
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("Cannot diarize missing or empty audio file.")
        pipeline = self._load_pipeline()
        diarization = pipeline(str(audio_path))
        segments: list[DiarizationSegment] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                DiarizationSegment(
                    start_time=float(turn.start),
                    end_time=float(turn.end),
                    speaker_id=f"speaker_{speaker}",
                )
            )
        if not segments:
            raise RuntimeError("Diarization produced no segments.")
        return DiarizationResult(segments=segments)


def get_diarization_service(provider: str) -> DiarizationService:
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeDiarizationService()
    if provider in ("pyannote", "pyannote.audio"):
        return PyannoteDiarizationService()
    raise ValueError(
        f"Unknown DIARIZATION_PROVIDER '{provider}'. Use 'fake' or 'pyannote'."
    )
