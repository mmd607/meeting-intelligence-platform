"""SQLAlchemy persistence models.

Tables: meetings, transcript_segments, semantic_entities.
Designed so a move to PostgreSQL only requires changing DATABASE_URL
(SQLAlchemy abstracts the dialect; no SQLite-specific SQL is used).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class MeetingRow(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled meeting")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)

    audio_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audio_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # v0.3 Semantic analysis status: null = not analyzed, "COMPLETED", "FAILED"
    semantic_analysis_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    segments: Mapped[list["TranscriptSegmentRow"]] = relationship(
        "TranscriptSegmentRow",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="TranscriptSegmentRow.start_time",
    )

    semantic_entities: Mapped[list["SemanticEntityRow"]] = relationship(
        "SemanticEntityRow",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )


class TranscriptSegmentRow(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Nullable in v0.1 — reserved for v0.2 speaker diarization. Never fake.
    speaker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    meeting: Mapped[MeetingRow] = relationship("MeetingRow", back_populates="segments")


class SemanticEntityRow(Base):
    __tablename__ = "semantic_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # TOPIC, PROBLEM, etc.
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID within the analysis result
    description: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    segment_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of ints
    start_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    meeting: Mapped[MeetingRow] = relationship("MeetingRow", back_populates="semantic_entities")
