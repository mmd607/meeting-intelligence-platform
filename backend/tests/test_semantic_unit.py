"""Tests for the semantic analysis service (unit-level)."""

from __future__ import annotations

import pytest

from backend.app.services.semantic.service import (
    FakeSemanticAnalysisService,
    TranscriptInput,
    get_semantic_analysis_service,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

CANONICAL_SEGMENTS = [
    TranscriptInput(segment_id=1, start_time=0.0, end_time=8.0, text="We need to reduce the API response time.", speaker_id="speaker_1"),
    TranscriptInput(segment_id=2, start_time=8.0, end_time=15.0, text="I think caching would solve most of the problem.", speaker_id="speaker_2"),
    TranscriptInput(segment_id=3, start_time=15.0, end_time=23.0, text="What about database indexing?", speaker_id="speaker_1"),
    TranscriptInput(segment_id=4, start_time=23.0, end_time=32.0, text="Let's use both caching and indexing.", speaker_id="speaker_2"),
    TranscriptInput(segment_id=5, start_time=32.0, end_time=40.0, text="Agreed. I'll handle the indexing work.", speaker_id="speaker_1"),
]


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


def test_fake_provider_returns_canonical_result():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    assert len(result.topics) == 1
    assert result.topics[0].description == "API performance"
    assert result.topics[0].segment_ids == [1, 2, 3, 4, 5]
    assert result.topics[0].start_time == 0.0
    assert result.topics[0].end_time == 40.0


def test_fake_provider_returns_problems():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    assert len(result.problems) == 1
    assert result.problems[0].description == "High API response time"
    assert result.problems[0].speaker_id == "speaker_1"
    assert result.problems[0].segment_ids == [1]


def test_fake_provider_returns_questions():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    assert len(result.questions) == 1
    assert result.questions[0].description == "What about database indexing?"
    assert result.questions[0].speaker_id == "speaker_1"
    assert result.questions[0].segment_ids == [3]


def test_fake_provider_returns_solutions():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    assert len(result.solutions) == 1
    assert result.solutions[0].description == "Caching and database indexing"
    assert result.solutions[0].speaker_id == "speaker_2"
    assert result.solutions[0].segment_ids == [2, 3, 4]


def test_fake_provider_returns_decisions():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    assert len(result.decisions) == 1
    assert result.decisions[0].description == "Use caching and database indexing"
    assert result.decisions[0].speaker_id == "speaker_2"
    assert result.decisions[0].segment_ids == [4]


def test_fake_provider_returns_action_items():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    assert len(result.action_items) == 1
    assert result.action_items[0].description == "Handle database indexing"
    assert result.action_items[0].speaker_id == "speaker_1"
    assert result.action_items[0].segment_ids == [5]


def test_fake_provider_source_grounding():
    """Every entity must reference valid transcript segment IDs."""
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)
    valid_ids = {s.segment_id for s in CANONICAL_SEGMENTS}

    for entity_list in [result.topics, result.problems, result.questions,
                        result.solutions, result.decisions, result.action_items]:
        for entity in entity_list:
            for seg_id in entity.segment_ids:
                assert seg_id in valid_ids, f"Invalid segment_id {seg_id}"


def test_fake_provider_timestamp_grounding():
    """Timestamps must be derived from source segments."""
    svc = FakeSemanticAnalysisService()
    result = svc.analyze(CANONICAL_SEGMENTS)

    for entity_list in [result.topics, result.problems, result.questions,
                        result.solutions, result.decisions, result.action_items]:
        for entity in entity_list:
            if entity.segment_ids:
                assert entity.start_time is not None
                assert entity.end_time is not None
                assert entity.start_time <= entity.end_time


def test_fake_provider_empty_segments():
    svc = FakeSemanticAnalysisService()
    result = svc.analyze([])
    assert result.topics == []
    assert result.problems == []
    assert result.questions == []
    assert result.solutions == []
    assert result.decisions == []
    assert result.action_items == []


def test_fake_provider_non_canonical_input():
    """Non-canonical input returns generic result with a topic."""
    svc = FakeSemanticAnalysisService()
    segments = [
        TranscriptInput(segment_id=1, start_time=0.0, end_time=5.0, text="Hello world.", speaker_id="speaker_1"),
    ]
    result = svc.analyze(segments)
    assert len(result.topics) == 1
    assert result.topics[0].description == "Discussion"


def test_fake_provider_questions_detected():
    """Questions ending with ? are detected in non-canonical input."""
    svc = FakeSemanticAnalysisService()
    segments = [
        TranscriptInput(segment_id=1, start_time=0.0, end_time=5.0, text="Is this working?", speaker_id="speaker_1"),
    ]
    result = svc.analyze(segments)
    assert len(result.questions) == 1
    assert result.questions[0].description == "Is this working?"
    assert result.questions[0].speaker_id == "speaker_1"


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def test_factory_fake():
    svc = get_semantic_analysis_service("fake")
    assert svc.name == "fake"


def test_factory_llm():
    svc = get_semantic_analysis_service("llm")
    assert svc.name == "llm"


def test_factory_unknown():
    with pytest.raises(ValueError):
        get_semantic_analysis_service("unknown_engine")
