"""Meeting repository: data-access abstraction.

Keeps SQLAlchemy session management out of business logic.
Designed so a move to PostgreSQL only requires changing DATABASE_URL.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.infrastructure.db import MeetingRow, TranscriptSegmentRow, SemanticEntityRow
from backend.app.services.transcription.service import TranscribedSegment
from backend.app.services.semantic.service import SemanticAnalysisResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MeetingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, title: str = "Untitled meeting", language: str | None = None) -> MeetingRow:
        meeting = MeetingRow(
            id=uuid.uuid4().hex,
            title=title,
            status="CREATED",
            created_at=_utcnow(),
            updated_at=_utcnow(),
            language=language,
        )
        self._session.add(meeting)
        self._session.commit()
        self._session.refresh(meeting)
        return meeting

    def get(self, meeting_id: str) -> MeetingRow | None:
        return self._session.get(MeetingRow, meeting_id)

    def update_status(self, meeting: MeetingRow, status: str, error_message: str | None = None) -> MeetingRow:
        meeting.status = status
        meeting.updated_at = _utcnow()
        if error_message is not None:
            meeting.error_message = error_message
        self._session.commit()
        self._session.refresh(meeting)
        return meeting

    def set_audio(
        self,
        meeting: MeetingRow,
        *,
        original_filename: str,
        stored_filename: str,
        mime: str | None,
        size_bytes: int,
        path: str,
    ) -> MeetingRow:
        meeting.audio_original_filename = original_filename
        meeting.audio_stored_filename = stored_filename
        meeting.audio_mime = mime
        meeting.audio_size_bytes = size_bytes
        meeting.audio_path = path
        meeting.updated_at = _utcnow()
        self._session.commit()
        self._session.refresh(meeting)
        return meeting

    def set_transcription_result(
        self,
        meeting: MeetingRow,
        segments: Sequence[TranscribedSegment],
        duration_seconds: float | None,
        language: str | None,
    ) -> list[TranscriptSegmentRow]:
        rows: list[TranscriptSegmentRow] = []
        for seg in segments:
            row = TranscriptSegmentRow(
                meeting_id=meeting.id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
                speaker_id=seg.speaker_id,
            )
            self._session.add(row)
            rows.append(row)
        if duration_seconds is not None:
            meeting.duration_seconds = duration_seconds
        if language is not None:
            meeting.language = language
        self._session.commit()
        for r in rows:
            self._session.refresh(r)
        return rows

    def get_segments(self, meeting_id: str) -> list[TranscriptSegmentRow]:
        stmt = (
            select(TranscriptSegmentRow)
            .where(TranscriptSegmentRow.meeting_id == meeting_id)
            .order_by(TranscriptSegmentRow.start_time)
        )
        return list(self._session.execute(stmt).scalars().all())

    # ------------------------------------------------------------------
    # V0.3 Semantic Analysis
    # ------------------------------------------------------------------

    def set_semantic_analysis_status(
        self, meeting: MeetingRow, status: str | None
    ) -> MeetingRow:
        meeting.semantic_analysis_status = status
        meeting.updated_at = _utcnow()
        self._session.commit()
        self._session.refresh(meeting)
        return meeting

    def set_semantic_analysis_result(
        self,
        meeting: MeetingRow,
        result: SemanticAnalysisResult,
    ) -> list[SemanticEntityRow]:
        """Persist semantic analysis result as individual entity rows."""
        import json

        # Delete any existing entities for this meeting
        existing = self._session.execute(
            select(SemanticEntityRow).where(SemanticEntityRow.meeting_id == meeting.id)
        ).scalars().all()
        for row in existing:
            self._session.delete(row)

        rows: list[SemanticEntityRow] = []
        entity_type_map = {
            "topics": "TOPIC",
            "problems": "PROBLEM",
            "questions": "QUESTION",
            "solutions": "SOLUTION",
            "decisions": "DECISION",
            "action_items": "ACTION_ITEM",
        }
        for attr, type_name in entity_type_map.items():
            entities = getattr(result, attr)
            for entity in entities:
                row = SemanticEntityRow(
                    meeting_id=meeting.id,
                    entity_type=type_name,
                    entity_id=entity.id,
                    description=entity.description,
                    speaker_id=entity.speaker_id,
                    segment_ids=json.dumps(entity.segment_ids),
                    start_time=entity.start_time,
                    end_time=entity.end_time,
                )
                self._session.add(row)
                rows.append(row)

        self._session.commit()
        for r in rows:
            self._session.refresh(r)
        return rows

    def get_semantic_entities(self, meeting_id: str) -> list[SemanticEntityRow]:
        stmt = (
            select(SemanticEntityRow)
            .where(SemanticEntityRow.meeting_id == meeting_id)
            .order_by(SemanticEntityRow.entity_type, SemanticEntityRow.entity_id)
        )
        return list(self._session.execute(stmt).scalars().all())
