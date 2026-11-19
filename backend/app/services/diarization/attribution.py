"""Temporal overlap attribution for v0.2.

Maps transcript segments to diarization speaker segments based on
maximum positive temporal overlap. Does not assume aligned boundaries.
"""

from __future__ import annotations

from backend.app.services.diarization.service import DiarizationSegment
from backend.app.services.transcription.service import TranscribedSegment


def _overlap(
    start_a: float, end_a: float, start_b: float, end_b: float
) -> float:
    overlap = min(end_a, end_b) - max(start_a, start_b)
    return max(overlap, 0.0)


def attribute_speakers(
    transcript_segments: Sequence[TranscribedSegment],
    diarization_segments: Sequence[DiarizationSegment],
) -> list[TranscribedSegment]:
    """Return new transcript segments with speaker_id populated.

    For each transcript segment, selects the diarization segment with
    the strongest positive temporal overlap. If no positive overlap
    exists, speaker_id remains None.
    """
    attributed: list[TranscribedSegment] = []
    for seg in transcript_segments:
        best_speaker: str | None = None
        best_overlap: float = 0.0
        for dseg in diarization_segments:
            overlap = _overlap(
                seg.start_time,
                seg.end_time,
                dseg.start_time,
                dseg.end_time,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = dseg.speaker_id
        attributed.append(
            TranscribedSegment(
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
                speaker_id=best_speaker,
            )
        )
    return attributed
