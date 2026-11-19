"""Tests for audio upload and validation."""

from __future__ import annotations

from io import BytesIO

from starlette.datastructures import UploadFile

from tests.conftest import _fake_audio_bytes


def test_upload_audio(client):
    create = client.post("/api/v1/meetings", json={"title": "Upload Test"})
    meeting_id = create.json()["id"]

    files = {"file": ("meeting.wav", _fake_audio_bytes(), "audio/wav")}
    resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "UPLOADED"
    assert data["audio"] is not None
    assert data["audio"]["original_filename"] == "meeting.wav"


def test_upload_empty_file(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]

    files = {"file": ("empty.wav", b"", "audio/wav")}
    resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    # Empty file may get 400 (EMPTY_UPLOAD) depending on validation path
    assert resp.status_code in (400, 422)


def test_upload_unsupported_format(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]

    files = {"file": ("data.pdf", b"%PDF-1.4 fake", "application/pdf")}
    resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_AUDIO_FILE"


def test_upload_to_nonexistent_meeting(client):
    files = {"file": ("test.wav", _fake_audio_bytes(), "audio/wav")}
    resp = client.post("/api/v1/meetings/nonexistent/audio", files=files)
    assert resp.status_code == 404


def test_upload_mp3(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]

    files = {"file": ("track.mp3", b"\xff\xfb\x90\x00" + b"\x00" * 100, "audio/mpeg")}
    resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert resp.status_code == 200
    assert resp.json()["audio"]["original_filename"] == "track.mp3"


def test_upload_m4a(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]

    files = {"file": ("recording.m4a", b"\x00\x00\x00\x20ftypM4A" + b"\x00" * 50, "audio/mp4")}
    resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert resp.status_code == 200


def test_audio_endpoint_not_found(client):
    resp = client.get("/api/v1/meetings/nonexistent/audio")
    assert resp.status_code == 404


def test_audio_endpoint_no_audio(client):
    create = client.post("/api/v1/meetings", json={})
    meeting_id = create.json()["id"]

    resp = client.get(f"/api/v1/meetings/{meeting_id}/audio")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NO_AUDIO"
