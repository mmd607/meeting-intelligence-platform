"""Pydantic request/response schemas. Consistent, typed API surface."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MeetingCreate(BaseModel):
    title: str = Field(default="Untitled meeting", max_length=255)
    language: str | None = Field(default=None, max_length=16)


class AudioMeta(BaseModel):
    original_filename: str | None = None
    mime: str | None = None
    size_bytes: int | None = None


class MeetingResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    language: str | None = None
    audio: AudioMeta | None = None
    duration: float | None = Field(default=None, alias="duration")
    error_message: str | None = None
    semantic_analysis_status: str | None = None

    model_config = {"populate_by_name": True}


class TranscriptSegmentResponse(BaseModel):
    id: int
    meeting_id: str
    start_time: float
    end_time: float
    text: str
    speaker_id: str | None = None


class TranscriptResponse(BaseModel):
    meeting_id: str
    status: str
    segments: list[TranscriptSegmentResponse]


# ---------------------------------------------------------------------------
# V0.3 Semantic Analysis Schemas
# ---------------------------------------------------------------------------


class SemanticEntityResponse(BaseModel):
    id: int
    description: str
    segment_ids: list[int] = Field(default_factory=list)
    speaker_id: str | None = None
    start_time: float | None = None
    end_time: float | None = None


class SemanticAnalysisResponse(BaseModel):
    meeting_id: str
    status: str | None = None  # null, "COMPLETED", "FAILED"
    topics: list[SemanticEntityResponse] = Field(default_factory=list)
    problems: list[SemanticEntityResponse] = Field(default_factory=list)
    questions: list[SemanticEntityResponse] = Field(default_factory=list)
    solutions: list[SemanticEntityResponse] = Field(default_factory=list)
    decisions: list[SemanticEntityResponse] = Field(default_factory=list)
    action_items: list[SemanticEntityResponse] = Field(default_factory=list)
