"""Domain layer: explicit meeting states and entities.

v0.1 scope: Meeting + Audio metadata + Transcript segments.
speaker_id is nullable to allow v0.2 diarization later — no fake speakers.
"""

from __future__ import annotations

import enum


class MeetingStatus(str, enum.Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
