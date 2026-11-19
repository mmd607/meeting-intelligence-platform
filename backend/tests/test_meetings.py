"""Tests for meeting creation and retrieval."""

from __future__ import annotations


def test_create_meeting(client):
    resp = client.post("/api/v1/meetings", json={"title": "Sprint Planning"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Sprint Planning"
    assert data["status"] == "CREATED"
    assert "id" in data


def test_create_meeting_default_title(client):
    resp = client.post("/api/v1/meetings", json={})
    assert resp.status_code == 201
    assert resp.json()["title"] == "Untitled meeting"


def test_get_meeting(client):
    create = client.post("/api/v1/meetings", json={"title": "Daily Standup"})
    meeting_id = create.json()["id"]

    resp = client.get(f"/api/v1/meetings/{meeting_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Daily Standup"


def test_get_meeting_not_found(client):
    resp = client.get("/api/v1/meetings/nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "MEETING_NOT_FOUND"


def test_create_meeting_with_language(client):
    resp = client.post("/api/v1/meetings", json={"title": "Retro", "language": "es"})
    assert resp.status_code == 201
    assert resp.json()["language"] == "es"
