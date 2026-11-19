"""Tests for transcription workflow."""

from __future__ import annotations

from tests.conftest import _fake_audio_bytes


def _upload_audio(client, meeting_id: str):
    files = {"file": ("test.wav", _fake_audio_bytes(), "audio/wav")}
    return client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)


def test_transcribe_success(client):
    create = client.post("/api/v1/meetings", json={"title": "Transcribe Test"})
    meeting_id = create.json()["id"]
    _upload_audio(client, meeting_id)

    resp = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"


def test_transcribe_without_audio(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]

    resp = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "NO_AUDIO"


def test_transcribe_nonexistent_meeting(client):
    resp = client.post("/api/v1/meetings/nonexistent/transcribe")
    assert resp.status_code == 404


def test_transcript_retrieval(client):
    create = client.post("/api/v1/meetings", json={"title": "Retrieve Transcript"})
    meeting_id = create.json()["id"]
    _upload_audio(client, meeting_id)
    client.post(f"/api/v1/meetings/{meeting_id}/transcribe")

    resp = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meeting_id"] == meeting_id
    assert data["status"] == "COMPLETED"
    assert len(data["segments"]) > 0

    seg = data["segments"][0]
    assert "start_time" in seg
    assert "end_time" in seg
    assert "text" in seg
    assert "speaker_id" in seg
    assert seg["speaker_id"] is None  # v0.1: no diarization


def test_transcript_segments_have_timestamps(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]
    _upload_audio(client, meeting_id)
    client.post(f"/api/v1/meetings/{meeting_id}/transcribe")

    resp = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    segments = resp.json()["segments"]
    for seg in segments:
        assert isinstance(seg["start_time"], float)
        assert isinstance(seg["end_time"], float)
        assert seg["end_time"] >= seg["start_time"]


def test_transcript_not_found(client):
    resp = client.get("/api/v1/meetings/nonexistent/transcript")
    assert resp.status_code == 404
