"""Storage abstraction so local FS can later be swapped for S3/cloud."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
import shutil
import uuid

from fastapi import UploadFile


class StorageService(ABC):
    @abstractmethod
    def save_meeting_audio(self, meeting_id: str, upload: UploadFile, extension: str) -> tuple[Path, str, int]:
        """Stream-upload audio to storage.

        Returns (absolute_path, stored_filename, size_bytes).
        Must not trust the user-provided filename for the stored path.
        """

    @abstractmethod
    def meeting_audio_path(self, meeting_id: str, stored_filename: str) -> Path:
        """Resolve the absolute path of a stored audio file."""

    @abstractmethod
    def delete_meeting_audio(self, meeting_id: str, stored_filename: str) -> None:
        ...


class LocalStorageService(StorageService):
    def __init__(self, root: Path):
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _meeting_dir(self, meeting_id: str) -> Path:
        # meeting_id is server-generated (uuid hex); safe path component.
        d = self._root / "audio" / meeting_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_meeting_audio(self, meeting_id: str, upload: UploadFile, extension: str) -> tuple[Path, str, int]:
        stored_filename = f"{uuid.uuid4().hex}{extension.lower()}"
        dest = self._meeting_dir(meeting_id) / stored_filename
        size = 0
        # Stream in chunks: avoid loading large files into memory.
        assert upload.file is not None
        with dest.open("wb") as out:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                out.write(chunk)
        return dest, stored_filename, size

    def meeting_audio_path(self, meeting_id: str, stored_filename: str) -> Path:
        # Guard against path traversal: only the basename is used.
        safe_name = Path(stored_filename).name
        return self._meeting_dir(meeting_id) / safe_name

    def delete_meeting_audio(self, meeting_id: str, stored_filename: str) -> None:
        try:
            self.meeting_audio_path(meeting_id, stored_filename).unlink(missing_ok=True)
        except OSError:
            pass


def ensure_storage_dirs(root: Path) -> None:
    (root / "audio").mkdir(parents=True, exist_ok=True)
