"""v1 API routes: meeting lifecycle (create, upload, transcribe, query)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import AppError
from backend.app.core.logging import get_logger
from backend.app.infrastructure.db import MeetingRow
from backend.app.repositories.meeting_repository import MeetingRepository
from backend.app.schemas.meeting import (
    AudioMeta,
    MeetingCreate,
    MeetingResponse,
    SemanticAnalysisResponse,
    SemanticEntityResponse,
    TranscriptResponse,
    TranscriptSegmentResponse,
)
from backend.app.services.audio_validation import validate_audio_upload
from backend.app.services.diarization.service import get_diarization_service
from backend.app.services.diarization.attribution import attribute_speakers
from backend.app.services.transcription.service import get_transcription_service
from backend.app.services.semantic.service import (
    TranscriptInput,
    get_semantic_analysis_service,
)

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])

# ---------------------------------------------------------------------------
# Dependency: SQLAlchemy session
# ---------------------------------------------------------------------------

_DB_SESSION: Session | None = None


def get_db() -> Session:
    """Yield a module-level session (sufficient for v0.1 single-process usage)."""
    global _DB_SESSION
    if _DB_SESSION is None:
        from backend.app.infrastructure.db import Base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        settings = get_settings()
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
        )
        Base.metadata.create_all(bind=engine)
        _DB_SESSION = sessionmaker(bind=engine)()
    return _DB_SESSION


def _repo(session: Session = Depends(get_db)) -> MeetingRepository:
    return MeetingRepository(session)


def _row_to_response(row: MeetingRow) -> MeetingResponse:
    return MeetingResponse(
        id=row.id,
        title=row.title,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        language=row.language,
        audio=AudioMeta(
            original_filename=row.audio_original_filename,
            mime=row.audio_mime,
            size_bytes=row.audio_size_bytes,
        ) if row.audio_stored_filename else None,
        duration=row.duration_seconds,
        error_message=row.error_message,
        semantic_analysis_status=row.semantic_analysis_status,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/meetings
# ---------------------------------------------------------------------------

@router.post("", response_model=MeetingResponse, status_code=201)
def create_meeting(body: MeetingCreate, repo: MeetingRepository = Depends(_repo)) -> MeetingResponse:
    log.info("Creating meeting: title=%s", body.title)
    row = repo.create(title=body.title, language=body.language)
    return _row_to_response(row)


# ---------------------------------------------------------------------------
# POST /api/v1/meetings/{meeting_id}/audio
# ---------------------------------------------------------------------------

@router.post("/{meeting_id}/audio", response_model=MeetingResponse)
async def upload_audio(
    meeting_id: str,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    repo: MeetingRepository = Depends(_repo),
) -> MeetingResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)

    ext = validate_audio_upload(
        file,
        max_size_bytes=settings.max_audio_size_bytes,
        declared_size=file.size,
    )

    repo.update_status(meeting, "UPLOADING")

    from backend.app.infrastructure.storage import LocalStorageService

    storage = LocalStorageService(settings.storage_root)
    abs_path, stored_name, size = storage.save_meeting_audio(meeting_id, file, ext)

    repo.set_audio(
        meeting,
        original_filename=file.filename or "unknown",
        stored_filename=stored_name,
        mime=file.content_type,
        size_bytes=size,
        path=str(abs_path),
    )
    repo.update_status(meeting, "UPLOADED")
    log.info("Audio uploaded: meeting=%s size=%d", meeting_id, size)
    return _row_to_response(meeting)


# ---------------------------------------------------------------------------
# POST /api/v1/meetings/{meeting_id}/transcribe
# ---------------------------------------------------------------------------

@router.post("/{meeting_id}/transcribe", response_model=MeetingResponse)
def start_transcription(
    meeting_id: str,
    settings: Settings = Depends(get_settings),
    repo: MeetingRepository = Depends(_repo),
) -> MeetingResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)
    if meeting.audio_path is None:
        raise AppError(code="NO_AUDIO", message="No audio uploaded for this meeting.", status_code=400)
    if meeting.status not in ("UPLOADED", "FAILED"):
        raise AppError(
            code="INVALID_STATE",
            message=f"Cannot transcribe in status '{meeting.status}'.",
            status_code=409,
        )

    repo.update_status(meeting, "PROCESSING")
    audio_path = Path(meeting.audio_path)
    try:
        svc = get_transcription_service(settings.TRANSCRIPTION_PROVIDER, settings.TRANSCRIPTION_MODEL)
        result = svc.transcribe(audio_path, language=meeting.language)
        diarization_segments = None
        if settings.DIARIZATION_ENABLED:
            log.info("Diarization started: meeting=%s", meeting_id)
            try:
                diar_svc = get_diarization_service(settings.DIARIZATION_PROVIDER)
                diar_result = diar_svc.diarize(audio_path)
                diarization_segments = diar_result.segments
                log.info(
                    "Diarization completed: meeting=%s segments=%d",
                    meeting_id,
                    len(diarization_segments),
                )
            except Exception as exc:
                log.warning("Diarization failed: meeting=%s error=%s", meeting_id, exc)
        if diarization_segments is not None:
            result.segments = attribute_speakers(result.segments, diarization_segments)
            log.info(
                "Speaker attribution completed: meeting=%s attributed=%d",
                meeting_id,
                sum(1 for s in result.segments if s.speaker_id is not None),
            )
        repo.set_transcription_result(meeting, result.segments, result.duration_seconds, result.language)
        repo.update_status(meeting, "COMPLETED")
        log.info("Transcription completed: meeting=%s segments=%d", meeting_id, len(result.segments))
    except Exception as exc:
        log.exception("Transcription failed: meeting=%s", meeting_id)
        repo.update_status(meeting, "FAILED", error_message=str(exc))

    return _row_to_response(meeting)


# ---------------------------------------------------------------------------
# GET /api/v1/meetings/{meeting_id}
# ---------------------------------------------------------------------------

@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: str, repo: MeetingRepository = Depends(_repo)) -> MeetingResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)
    return _row_to_response(meeting)


# ---------------------------------------------------------------------------
# GET /api/v1/meetings/{meeting_id}/transcript
# ---------------------------------------------------------------------------

@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
def get_transcript(meeting_id: str, repo: MeetingRepository = Depends(_repo)) -> TranscriptResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)
    segments = repo.get_segments(meeting_id)
    return TranscriptResponse(
        meeting_id=meeting_id,
        status=meeting.status,
        segments=[
            TranscriptSegmentResponse(
                id=s.id,
                meeting_id=s.meeting_id,
                start_time=s.start_time,
                end_time=s.end_time,
                text=s.text,
                speaker_id=s.speaker_id,
            )
            for s in segments
        ],
    )


# ---------------------------------------------------------------------------
# GET /api/v1/meetings/{meeting_id}/audio
# ---------------------------------------------------------------------------

from fastapi.responses import FileResponse


@router.get("/{meeting_id}/audio")
def get_audio(meeting_id: str, repo: MeetingRepository = Depends(_repo)) -> FileResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)
    if meeting.audio_path is None or meeting.audio_stored_filename is None:
        raise AppError(code="NO_AUDIO", message="No audio available.", status_code=404)

    from backend.app.infrastructure.storage import LocalStorageService
    from backend.app.core.config import get_settings

    settings = get_settings()
    storage = LocalStorageService(settings.storage_root)
    path = storage.meeting_audio_path(meeting_id, meeting.audio_stored_filename)
    if not path.exists():
        raise AppError(code="AUDIO_MISSING", message="Audio file not found on disk.", status_code=404)

    media_type = meeting.audio_mime or "application/octet-stream"
    return FileResponse(path=str(path), media_type=media_type, filename=meeting.audio_original_filename)


# ---------------------------------------------------------------------------
# POST /api/v1/meetings/{meeting_id}/analyze
# ---------------------------------------------------------------------------

@router.post("/{meeting_id}/analyze", response_model=MeetingResponse)
def start_semantic_analysis(
    meeting_id: str,
    settings: Settings = Depends(get_settings),
    repo: MeetingRepository = Depends(_repo),
) -> MeetingResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)
    if meeting.status != "COMPLETED":
        raise AppError(
            code="INVALID_STATE",
            message=f"Cannot analyze in status '{meeting.status}'. Transcribe first.",
            status_code=409,
        )

    segments = repo.get_segments(meeting_id)
    if not segments:
        raise AppError(code="NO_TRANSCRIPT", message="No transcript segments to analyze.", status_code=400)

    # Build transcript input from persisted segments
    transcript_input = [
        TranscriptInput(
            segment_id=s.id,
            start_time=s.start_time,
            end_time=s.end_time,
            text=s.text,
            speaker_id=s.speaker_id,
        )
        for s in segments
    ]

    log.info(
        "Semantic analysis started: meeting=%s provider=%s segments=%d",
        meeting_id,
        settings.SEMANTIC_ANALYSIS_PROVIDER,
        len(transcript_input),
    )

    try:
        svc = get_semantic_analysis_service(settings.SEMANTIC_ANALYSIS_PROVIDER)
        result = svc.analyze(transcript_input)
        repo.set_semantic_analysis_result(meeting, result)
        repo.set_semantic_analysis_status(meeting, "COMPLETED")
        total_entities = (
            len(result.topics)
            + len(result.problems)
            + len(result.questions)
            + len(result.solutions)
            + len(result.decisions)
            + len(result.action_items)
        )
        log.info(
            "Semantic analysis completed: meeting=%s entities=%d",
            meeting_id,
            total_entities,
        )
    except Exception as exc:
        log.exception("Semantic analysis failed: meeting=%s", meeting_id)
        repo.set_semantic_analysis_status(meeting, "FAILED")

    return _row_to_response(meeting)


# ---------------------------------------------------------------------------
# GET /api/v1/meetings/{meeting_id}/analysis
# ---------------------------------------------------------------------------

_EntityTypeMap = {
    "TOPIC": "topics",
    "PROBLEM": "problems",
    "QUESTION": "questions",
    "SOLUTION": "solutions",
    "DECISION": "decisions",
    "ACTION_ITEM": "action_items",
}


@router.get("/{meeting_id}/analysis", response_model=SemanticAnalysisResponse)
def get_semantic_analysis(
    meeting_id: str,
    repo: MeetingRepository = Depends(_repo),
) -> SemanticAnalysisResponse:
    meeting = repo.get(meeting_id)
    if meeting is None:
        raise AppError(code="MEETING_NOT_FOUND", message="Meeting not found.", status_code=404)

    entities = repo.get_semantic_entities(meeting_id)

    # Group entities by type
    grouped: dict[str, list[SemanticEntityResponse]] = {
        "topics": [],
        "problems": [],
        "questions": [],
        "solutions": [],
        "decisions": [],
        "action_items": [],
    }
    for entity in entities:
        field_name = _EntityTypeMap.get(entity.entity_type)
        if field_name is None:
            continue
        seg_ids = json.loads(entity.segment_ids) if entity.segment_ids else []
        grouped[field_name].append(
            SemanticEntityResponse(
                id=entity.entity_id,
                description=entity.description,
                segment_ids=seg_ids,
                speaker_id=entity.speaker_id,
                start_time=entity.start_time,
                end_time=entity.end_time,
            )
        )

    return SemanticAnalysisResponse(
        meeting_id=meeting_id,
        status=meeting.semantic_analysis_status,
        topics=grouped["topics"],
        problems=grouped["problems"],
        questions=grouped["questions"],
        solutions=grouped["solutions"],
        decisions=grouped["decisions"],
        action_items=grouped["action_items"],
    )
