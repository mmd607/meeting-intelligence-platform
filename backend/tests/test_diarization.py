"""Tests for the diarization workflow integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import _fake_audio_bytes


def _upload_audio(client, meeting_id: str):
    files = {"file": ("test.wav", _fake_audio_bytes(), "audio/wav")}
    return client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)


# ---------------------------------------------------------------------------
# Diarization enabled (integration with mocked diarization service)
# ---------------------------------------------------------------------------


def test_transcribe_with_diarization_enabled(client):
    from backend.app.services.diarization.service import DiarizationResult, DiarizationSegment

    fake_diar_result = DiarizationResult(
        segments=[
            DiarizationSegment(0.0, 5.0, "speaker_1"),
            DiarizationSegment(5.0, 10.0, "speaker_2"),
            DiarizationSegment(10.0, 15.0, "speaker_1"),
        ]
    )

    with (
        patch("backend.app.api.v1.meetings.get_diarization_service") as mock_get_diar,
        patch("backend.app.api.v1.meetings.get_settings") as mock_get_settings,
    ):
        mock_get_diar.return_value.diarize.return_value = fake_diar_result
        mock_settings = MagicMock()
        mock_settings.DIARIZATION_ENABLED = True
        mock_settings.DIARIZATION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_MODEL = "tiny"
        mock_settings.max_audio_size_bytes = 500 * 1024 * 1024
        mock_settings.storage_root = "/tmp"
        mock_get_settings.return_value = mock_settings

        create = client.post("/api/v1/meetings", json={"title": "Diarization Test"})
        meeting_id = create.json()["id"]
        _upload_audio(client, meeting_id)

        resp = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"


def test_transcribe_diarization_populates_speaker_id(client):
    from backend.app.services.diarization.service import DiarizationResult, DiarizationSegment

    fake_diar_result = DiarizationResult(
        segments=[
            DiarizationSegment(0.0, 5.0, "speaker_1"),
            DiarizationSegment(5.0, 10.0, "speaker_2"),
        ]
    )

    with (
        patch("backend.app.api.v1.meetings.get_diarization_service") as mock_get_diar,
        patch("backend.app.api.v1.meetings.get_settings") as mock_get_settings,
    ):
        mock_get_diar.return_value.diarize.return_value = fake_diar_result
        mock_settings = MagicMock()
        mock_settings.DIARIZATION_ENABLED = True
        mock_settings.DIARIZATION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_MODEL = "tiny"
        mock_settings.max_audio_size_bytes = 500 * 1024 * 1024
        mock_settings.storage_root = "/tmp"
        mock_get_settings.return_value = mock_settings

        create = client.post("/api/v1/meetings", json={"title": "Speaker ID Test"})
        meeting_id = create.json()["id"]
        _upload_audio(client, meeting_id)
        client.post(f"/api/v1/meetings/{meeting_id}/transcribe")

        resp = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["segments"]) > 0
        for seg in data["segments"]:
            assert "speaker_id" in seg


def test_transcribe_diarization_failure_preserves_transcription(client):
    with (
        patch("backend.app.api.v1.meetings.get_diarization_service") as mock_get_diar,
        patch("backend.app.api.v1.meetings.get_settings") as mock_get_settings,
    ):
        mock_get_diar.return_value.diarize.side_effect = RuntimeError("Diarization model not found")
        mock_settings = MagicMock()
        mock_settings.DIARIZATION_ENABLED = True
        mock_settings.DIARIZATION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_MODEL = "tiny"
        mock_settings.max_audio_size_bytes = 500 * 1024 * 1024
        mock_settings.storage_root = "/tmp"
        mock_get_settings.return_value = mock_settings

        create = client.post("/api/v1/meetings", json={"title": "Diarization Failure Test"})
        meeting_id = create.json()["id"]
        _upload_audio(client, meeting_id)

        resp = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"

        resp2 = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
        assert resp2.status_code == 200
        transcript = resp2.json()
        assert len(transcript["segments"]) > 0
        for seg in transcript["segments"]:
            assert seg["speaker_id"] is None


# ---------------------------------------------------------------------------
# Diarization disabled (V0.1 behavior preserved)
# ---------------------------------------------------------------------------


def test_transcribe_diarization_disabled(client):
    with patch("backend.app.api.v1.meetings.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.DIARIZATION_ENABLED = False
        mock_settings.TRANSCRIPTION_PROVIDER = "fake"
        mock_settings.TRANSCRIPTION_MODEL = "tiny"
        mock_settings.max_audio_size_bytes = 500 * 1024 * 1024
        mock_settings.storage_root = "/tmp"
        mock_get_settings.return_value = mock_settings

        create = client.post("/api/v1/meetings", json={"title": "No Diarization"})
        meeting_id = create.json()["id"]
        _upload_audio(client, meeting_id)

        resp = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"

        resp2 = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
        assert resp2.status_code == 200
        transcript = resp2.json()
        assert len(transcript["segments"]) > 0
        for seg in transcript["segments"]:
            assert seg["speaker_id"] is None
