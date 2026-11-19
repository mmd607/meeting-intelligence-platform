"""Tests for the semantic analysis workflow integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import _fake_audio_bytes


def _upload_audio(client, meeting_id: str):
    files = {"file": ("test.wav", _fake_audio_bytes(), "audio/wav")}
    return client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)


def _transcribe(client, meeting_id: str):
    return client.post(f"/api/v1/meetings/{meeting_id}/transcribe")


def _upload_and_transcribe(client, meeting_id: str):
    _upload_audio(client, meeting_id)
    return _transcribe(client, meeting_id)


# ---------------------------------------------------------------------------
# Semantic analysis integration tests
# ---------------------------------------------------------------------------


def test_analyze_requires_completed_status(client):
    create = client.post("/api/v1/meetings", json={"title": "Test"})
    meeting_id = create.json()["id"]
    _upload_audio(client, meeting_id)

    resp = client.post(f"/api/v1/meetings/{meeting_id}/analyze")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_STATE"


def test_analyze_nonexistent_meeting(client):
    resp = client.post("/api/v1/meetings/nonexistent/analyze")
    assert resp.status_code == 404


def test_analyze_success(client):
    create = client.post("/api/v1/meetings", json={"title": "Analyze Test"})
    meeting_id = create.json()["id"]
    _upload_and_transcribe(client, meeting_id)

    resp = client.post(f"/api/v1/meetings/{meeting_id}/analyze")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["semantic_analysis_status"] == "COMPLETED"


def test_analysis_retrieval(client):
    create = client.post("/api/v1/meetings", json={"title": "Retrieval Test"})
    meeting_id = create.json()["id"]
    _upload_and_transcribe(client, meeting_id)
    client.post(f"/api/v1/meetings/{meeting_id}/analyze")

    resp = client.get(f"/api/v1/meetings/{meeting_id}/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meeting_id"] == meeting_id
    assert data["status"] == "COMPLETED"
    assert isinstance(data["topics"], list)
    assert isinstance(data["problems"], list)
    assert isinstance(data["questions"], list)
    assert isinstance(data["solutions"], list)
    assert isinstance(data["decisions"], list)
    assert isinstance(data["action_items"], list)


def test_analysis_nonexistent_meeting(client):
    resp = client.get("/api/v1/meetings/nonexistent/analysis")
    assert resp.status_code == 404


def test_analysis_before_analyze(client):
    """Analysis retrieval before running analysis returns empty lists."""
    create = client.post("/api/v1/meetings", json={"title": "Empty Analysis"})
    meeting_id = create.json()["id"]
    _upload_and_transcribe(client, meeting_id)

    resp = client.get(f"/api/v1/meetings/{meeting_id}/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] is None
    assert len(data["topics"]) == 0
    assert len(data["problems"]) == 0
    assert len(data["questions"]) == 0
    assert len(data["solutions"]) == 0
    assert len(data["decisions"]) == 0
    assert len(data["action_items"]) == 0


def test_semantic_failure_preserves_transcript(client):
    """If semantic analysis fails, transcript remains intact."""
    create = client.post("/api/v1/meetings", json={"title": "Failure Test"})
    meeting_id = create.json()["id"]
    _upload_and_transcribe(client, meeting_id)

    with patch("backend.app.api.v1.meetings.get_semantic_analysis_service") as mock_svc:
        mock_svc.return_value.analyze.side_effect = RuntimeError("Analysis failed")
        resp = client.post(f"/api/v1/meetings/{meeting_id}/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["semantic_analysis_status"] == "FAILED"

    # Transcript should still be available
    resp2 = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    assert resp2.status_code == 200
    assert len(resp2.json()["segments"]) > 0


def test_analyze_with_mocked_provider(client):
    """Integration test with mocked semantic analysis provider."""
    from backend.app.services.semantic.service import (
        SemanticAnalysisResult,
        Topic,
        Problem,
        Decision,
        ActionItem,
    )

    fake_result = SemanticAnalysisResult(
        topics=[Topic(id=1, description="Test Topic", segment_ids=[1], start_time=0.0, end_time=5.0)],
        problems=[Problem(id=1, description="Test Problem", speaker_id="speaker_1", segment_ids=[1])],
        decisions=[Decision(id=1, description="Test Decision", speaker_id="speaker_2", segment_ids=[2])],
        action_items=[ActionItem(id=1, description="Test Action", speaker_id="speaker_1", segment_ids=[3])],
    )

    with patch("backend.app.api.v1.meetings.get_semantic_analysis_service") as mock_get_svc:
        mock_get_svc.return_value.analyze.return_value = fake_result
        mock_get_svc.return_value.name = "fake"

        create = client.post("/api/v1/meetings", json={"title": "Mocked Test"})
        meeting_id = create.json()["id"]
        _upload_and_transcribe(client, meeting_id)

        resp = client.post(f"/api/v1/meetings/{meeting_id}/analyze")
        assert resp.status_code == 200
        assert resp.json()["semantic_analysis_status"] == "COMPLETED"

        resp2 = client.get(f"/api/v1/meetings/{meeting_id}/analysis")
        data = resp2.json()
        assert len(data["topics"]) == 1
        assert data["topics"][0]["description"] == "Test Topic"
        assert len(data["problems"]) == 1
        assert len(data["decisions"]) == 1
        assert len(data["action_items"]) == 1
        assert data["action_items"][0]["speaker_id"] == "speaker_1"
