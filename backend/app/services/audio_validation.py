"""Audio validation for v0.1.

Validates extension, non-empty payload, and size limit.
MIME type is checked where practical (loose allow-list, since browsers
report m4a/mp3 inconsistently). Never trust extension alone: empty
payloads are rejected and transcription will fail loudly on corrupt data.
"""

from __future__ import annotations

from fastapi import UploadFile

from backend.app.core.errors import AppError

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}

# Loose allow-list: browsers vary (e.g. audio/x-m4a, audio/mp4, application/octet-stream).
ALLOWED_MIME_PREFIXES = ("audio/",)
ALLOWED_MIME_EXACT = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/aac",
    "application/octet-stream",
    "",
}


def _extension_of(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def validate_audio_upload(
    upload: UploadFile | None,
    *,
    max_size_bytes: int,
    declared_size: int | None = None,
) -> str:
    """Validate an upload. Returns the normalised extension (e.g. '.wav').

    Raises AppError with codes: EMPTY_UPLOAD, INVALID_AUDIO_FILE, FILE_TOO_LARGE.
    """
    if upload is None or upload.filename is None or upload.filename.strip() == "":
        raise AppError(code="EMPTY_UPLOAD", message="No audio file was provided.", status_code=400)

    ext = _extension_of(upload.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            code="INVALID_AUDIO_FILE",
            message=f"Unsupported audio format '{ext or 'unknown'}'. Supported: .wav, .mp3, .m4a.",
            status_code=400,
        )

    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime and mime not in ALLOWED_MIME_EXACT and not mime.startswith(ALLOWED_MIME_PREFIXES):
        raise AppError(
            code="INVALID_AUDIO_FILE",
            message="The uploaded file could not be processed.",
            status_code=400,
        )

    if declared_size is not None:
        if declared_size <= 0:
            raise AppError(code="EMPTY_UPLOAD", message="The uploaded file is empty.", status_code=400)
        if declared_size > max_size_bytes:
            raise AppError(
                code="FILE_TOO_LARGE",
                message=f"File exceeds the {max_size_bytes // (1024 * 1024)} MB limit.",
                status_code=413,
            )
    return ext
