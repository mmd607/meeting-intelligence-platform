"""Semantic analysis abstraction (v0.3).

Application code depends only on SemanticAnalysisService; the concrete
engine (fake / llm) is chosen via config + factory.

Extracts structured semantic information from a speaker-aware transcript:
topics, problems, questions, solutions, decisions, and action items.
Every extracted entity references source transcript segments.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass
class SemanticEntity:
    """Base for all semantic entities with source grounding."""

    id: int
    description: str
    segment_ids: list[int] = field(default_factory=list)
    speaker_id: str | None = None
    start_time: float | None = None
    end_time: float | None = None


@dataclass
class Topic(SemanticEntity):
    pass


@dataclass
class Problem(SemanticEntity):
    pass


@dataclass
class Question(SemanticEntity):
    pass


@dataclass
class Solution(SemanticEntity):
    pass


@dataclass
class Decision(SemanticEntity):
    pass


@dataclass
class ActionItem(SemanticEntity):
    pass


@dataclass
class SemanticAnalysisResult:
    topics: list[Topic] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    solutions: list[Solution] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)


@dataclass
class TranscriptInput:
    """Lightweight transcript representation for the analysis service."""

    segment_id: int
    start_time: float
    end_time: float
    text: str
    speaker_id: str | None = None


class SemanticAnalysisService(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, segments: Sequence[TranscriptInput]) -> SemanticAnalysisResult:
        """Analyze transcript segments and return structured semantic entities."""


class FakeSemanticAnalysisService(SemanticAnalysisService):
    """Deterministic stub for dev/tests. No external calls, no model.

    When fed the canonical 5-segment fixture, returns deterministic results.
    For other inputs, returns a generic single-topic result.
    """

    name = "fake"

    # Canonical fixture text patterns
    _CANONICAL_TEXTS = [
        "We need to reduce the API response time.",
        "I think caching would solve most of the problem.",
        "What about database indexing?",
        "Let's use both caching and indexing.",
        "Agreed. I'll handle the indexing work.",
    ]

    def analyze(self, segments: Sequence[TranscriptInput]) -> SemanticAnalysisResult:
        if not segments:
            return SemanticAnalysisResult()

        texts = [s.text.strip().rstrip(".").lower() for s in segments]
        seg_ids = [s.segment_id for s in segments]
        seg_map = {s.segment_id: s for s in segments}

        # Check if this matches the canonical fixture
        is_canonical = len(segments) == 5 and all(
            self._CANONICAL_TEXTS[i].rstrip(".").lower() == texts[i]
            for i in range(5)
        )

        if is_canonical:
            return self._canonical_result(segments)

        # Generic fallback: extract one topic from all segments
        first = segments[0]
        last = segments[-1]
        topic = Topic(
            id=1,
            description="Discussion",
            segment_ids=seg_ids,
            start_time=first.start_time,
            end_time=last.end_time,
        )

        problems: list[Problem] = []
        questions: list[Question] = []
        solutions: list[Solution] = []
        decisions: list[Decision] = []
        action_items: list[ActionItem] = []

        for seg in segments:
            text = seg.text.strip()
            if text.endswith("?"):
                questions.append(
                    Question(
                        id=len(questions) + 1,
                        description=text,
                        speaker_id=seg.speaker_id,
                        segment_ids=[seg.segment_id],
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                    )
                )

        return SemanticAnalysisResult(
            topics=[topic],
            problems=problems,
            questions=questions,
            solutions=solutions,
            decisions=decisions,
            action_items=action_items,
        )

    def _canonical_result(self, segments: Sequence[TranscriptInput]) -> SemanticAnalysisResult:
        """Return deterministic results for the canonical 5-segment test fixture."""
        s1, s2, s3, s4, s5 = segments

        return SemanticAnalysisResult(
            topics=[
                Topic(
                    id=1,
                    description="API performance",
                    segment_ids=[s1.segment_id, s2.segment_id, s3.segment_id, s4.segment_id, s5.segment_id],
                    start_time=s1.start_time,
                    end_time=s5.end_time,
                ),
            ],
            problems=[
                Problem(
                    id=1,
                    description="High API response time",
                    speaker_id=s1.speaker_id,
                    segment_ids=[s1.segment_id],
                    start_time=s1.start_time,
                    end_time=s1.end_time,
                ),
            ],
            questions=[
                Question(
                    id=1,
                    description="What about database indexing?",
                    speaker_id=s3.speaker_id,
                    segment_ids=[s3.segment_id],
                    start_time=s3.start_time,
                    end_time=s3.end_time,
                ),
            ],
            solutions=[
                Solution(
                    id=1,
                    description="Caching and database indexing",
                    speaker_id=s2.speaker_id,
                    segment_ids=[s2.segment_id, s3.segment_id, s4.segment_id],
                    start_time=s2.start_time,
                    end_time=s4.end_time,
                ),
            ],
            decisions=[
                Decision(
                    id=1,
                    description="Use caching and database indexing",
                    speaker_id=s4.speaker_id,
                    segment_ids=[s4.segment_id],
                    start_time=s4.start_time,
                    end_time=s4.end_time,
                ),
            ],
            action_items=[
                ActionItem(
                    id=1,
                    description="Handle database indexing",
                    speaker_id=s5.speaker_id,
                    segment_ids=[s5.segment_id],
                    start_time=s5.start_time,
                    end_time=s5.end_time,
                ),
            ],
        )


class LLMSemanticAnalysisService(SemanticAnalysisService):
    """LLM-based semantic analysis via configurable provider.

    Requires an LLM API key configured via environment. The provider
    abstraction is isolated behind this class; the rest of the app
    does not depend on any specific LLM SDK.
    """

    name = "llm"

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini") -> None:
        self._provider = provider
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self._provider == "openai":
                try:
                    import openai
                except ImportError as exc:
                    raise RuntimeError(
                        "openai package is not installed. "
                        "Run `pip install openai` or set SEMANTIC_ANALYSIS_PROVIDER=fake."
                    ) from exc
                self._client = openai.OpenAI()
            else:
                raise RuntimeError(f"Unsupported LLM provider: {self._provider}")
        return self._client

    def analyze(self, segments: Sequence[TranscriptInput]) -> SemanticAnalysisResult:
        if not segments:
            return SemanticAnalysisResult()

        transcript_text = self._format_transcript(segments)
        prompt = self._build_prompt(transcript_text)
        raw_response = self._call_llm(prompt)
        return self._parse_response(raw_response, segments)

    def _format_transcript(self, segments: Sequence[TranscriptInput]) -> str:
        lines: list[str] = []
        for seg in segments:
            speaker = seg.speaker_id or "unknown"
            lines.append(f"[Segment {seg.id} | {seg.start_time:.1f}s - {seg.end_time:.1f}s] {speaker}: {seg.text}")
        return "\n".join(lines)

    def _build_prompt(self, transcript_text: str) -> str:
        return (
            "Analyze the following meeting transcript and extract structured semantic information.\n\n"
            "For each entity type, return a JSON array. Each entity must have:\n"
            "- id: integer (sequential starting from 1)\n"
            "- description: string\n"
            "- segment_ids: list of integers (source transcript segment IDs)\n"
            "- speaker_id: string or null (who said it, if applicable)\n\n"
            "Entity types to extract:\n"
            "- topics: meaningful discussion themes (avoid per-sentence topics)\n"
            "- problems: explicitly mentioned problems, blockers, issues\n"
            "- questions: explicit questions raised\n"
            "- solutions: proposed solutions (not necessarily decided)\n"
            "- decisions: explicitly agreed outcomes\n"
            "- action_items: tasks someone committed to doing\n\n"
            "Return ONLY valid JSON with this structure:\n"
            '{"topics": [...], "problems": [...], "questions": [...], '
            '"solutions": [...], "decisions": [...], "action_items": [...]}\n\n'
            "Transcript:\n"
            f"{transcript_text}\n\n"
            "JSON response:"
        )

    def _call_llm(self, prompt: str) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    def _parse_response(self, raw: str, segments: Sequence[TranscriptInput]) -> SemanticAnalysisResult:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return SemanticAnalysisResult()

        seg_ids = {s.id for s in segments}
        seg_map = {s.id: s for s in segments}

        def _parse_entities(items: list[dict], cls: type) -> list:
            result = []
            for item in items:
                entity_seg_ids = [sid for sid in item.get("segment_ids", []) if sid in seg_ids]
                if not entity_seg_ids:
                    continue
                times = [seg_map[sid] for sid in entity_seg_ids if sid in seg_map]
                result.append(
                    cls(
                        id=item.get("id", len(result) + 1),
                        description=item.get("description", ""),
                        segment_ids=entity_seg_ids,
                        speaker_id=item.get("speaker_id"),
                        start_time=min(t.start_time for t in times) if times else None,
                        end_time=max(t.end_time for t in times) if times else None,
                    )
                )
            return result

        return SemanticAnalysisResult(
            topics=_parse_entities(data.get("topics", []), Topic),
            problems=_parse_entities(data.get("problems", []), Problem),
            questions=_parse_entities(data.get("questions", []), Question),
            solutions=_parse_entities(data.get("solutions", []), Solution),
            decisions=_parse_entities(data.get("decisions", []), Decision),
            action_items=_parse_entities(data.get("action_items", []), ActionItem),
        )


def get_semantic_analysis_service(provider: str) -> SemanticAnalysisService:
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeSemanticAnalysisService()
    if provider in ("llm", "openai"):
        return LLMSemanticAnalysisService(provider="openai")
    raise ValueError(
        f"Unknown SEMANTIC_ANALYSIS_PROVIDER '{provider}'. Use 'fake' or 'llm'."
    )
