"""Transcription abstraction (spec section 9).

Application code depends only on TranscriptionService; the concrete
engine (fake / whisper) is chosen via config + factory. Output always
preserves timestamps; speaker_id stays None in v0.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TranscribedSegment:
    start_time: float
    end_time: float
    text: str
    speaker_id: str | None = None  # always None in v0.1


@dataclass
class TranscriptionResult:
    segments: list[TranscribedSegment] = field(default_factory=list)
    language: str | None = None
    duration_seconds: float | None = None


class TranscriptionService(ABC):
    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str | None = None) -> TranscriptionResult:
        """Transcribe audio file -> timestamped segments. Raises on failure."""


class FakeTranscriptionService(TranscriptionService):
    """Deterministic stub for dev/tests. No external calls, no model."""

    name = "fake"

    def transcribe(self, audio_path: Path, language: str | None = None) -> TranscriptionResult:
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("Cannot transcribe missing or empty audio file.")
        return TranscriptionResult(
            segments=[
                TranscribedSegment(0.0, 4.82, "Hello everyone, let's start the meeting."),
                TranscribedSegment(5.0, 9.4, "Today we're going to discuss the new system."),
                TranscribedSegment(10.0, 14.2, "We should redesign the authentication system."),
            ],
            language=language or "en",
            duration_seconds=14.2,
        )


class WhisperTranscriptionService(TranscriptionService):
    """Whisper-compatible engine via faster-whisper (lazy import).

    Requires: pip install faster-whisper. Model selected via TRANSCRIPTION_MODEL
    (e.g. tiny, base, small, medium). Downloads model on first use.
    """

    name = "whisper"

    def __init__(self, model_name: str = "tiny"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is not installed. Run `pip install faster-whisper` "
                    "or set TRANSCRIPTION_PROVIDER=fake."
                ) from exc
            self._model = WhisperModel(self._model_name, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: Path, language: str | None = None) -> TranscriptionResult:
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("Cannot transcribe missing or empty audio file.")
        model = self._load_model()
        segments_iter, info = model.transcribe(str(audio_path), language=language, beam_size=1)
        out: list[TranscribedSegment] = []
        for s in segments_iter:
            text = (s.text or "").strip()
            if not text:
                continue
            out.append(TranscribedSegment(float(s.start), float(s.end), text))
        if not out:
            raise RuntimeError("Transcription produced no segments.")
        duration = getattr(info, "duration", None)
        language_out = getattr(info, "language", language)
        return TranscriptionResult(segments=out, language=language_out, duration_seconds=duration)


def get_transcription_service(provider: str, model: str = "tiny") -> TranscriptionService:
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeTranscriptionService()
    if provider in ("whisper", "faster-whisper", "faster_whisper"):
        return WhisperTranscriptionService(model_name=model)
    raise ValueError(f"Unknown TRANSCRIPTION_PROVIDER '{provider}'. Use 'fake' or 'whisper'.")
