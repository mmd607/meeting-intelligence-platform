import { useState, useEffect } from "react";
import type { SemanticAnalysisResponse, SemanticEntity, TranscriptSegment } from "../types";
import { getSemanticAnalysis, getTranscript } from "../services/api";

interface Props {
  meetingId: string;
  onSeek?: (time: number) => void;
  activeSegmentId?: number | null;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function speakerLabel(speakerId: string | null): string | null {
  if (!speakerId) return null;
  const parts = speakerId.split("_");
  const num = parts[parts.length - 1];
  return `Speaker ${num}`;
}

function EntitySection({
  title,
  entities,
  segments,
  onSeek,
  activeSegmentId,
}: {
  title: string;
  entities: SemanticEntity[];
  segments: TranscriptSegment[];
  onSeek?: (time: number) => void;
  activeSegmentId?: number | null;
}) {
  if (entities.length === 0) return null;

  const segMap = new Map(segments.map((s) => [s.id, s]));

  return (
    <div className="semantic-section">
      <h3>{title}</h3>
      {entities.map((entity) => (
        <div key={entity.id} className="semantic-entity">
          <p className="entity-description">{entity.description}</p>
          {entity.speaker_id && (
            <span className="entity-speaker">{speakerLabel(entity.speaker_id)}</span>
          )}
          {entity.segment_ids.length > 0 && (
            <div className="entity-sources">
              {entity.segment_ids.map((segId) => {
                const seg = segMap.get(segId);
                if (!seg) return null;
                const isActive = activeSegmentId === segId;
                return (
                  <button
                    key={segId}
                    className={`source-link ${isActive ? "active" : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSeek?.(seg.start_time);
                    }}
                    title={`Jump to ${formatTime(seg.start_time)}: "${seg.text}"`}
                  >
                    {formatTime(seg.start_time)}
                    {seg.speaker_id && ` (${speakerLabel(seg.speaker_id)})`}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function SemanticAnalysisView({ meetingId, onSeek, activeSegmentId }: Props) {
  const [analysis, setAnalysis] = useState<SemanticAnalysisResponse | null>(null);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [analysisData, transcriptData] = await Promise.all([
          getSemanticAnalysis(meetingId),
          getTranscript(meetingId),
        ]);
        if (!cancelled) {
          setAnalysis(analysisData);
          setSegments(transcriptData.segments);
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [meetingId]);

  if (loading) return <div className="card">Loading analysis...</div>;
  if (error) return <div className="card error">{error}</div>;
  if (!analysis) return null;

  const totalEntities =
    analysis.topics.length +
    analysis.problems.length +
    analysis.questions.length +
    analysis.solutions.length +
    analysis.decisions.length +
    analysis.action_items.length;

  if (totalEntities === 0) {
    return (
      <div className="card">
        <h2>Semantic Analysis</h2>
        <p className="empty">No semantic entities extracted.</p>
      </div>
    );
  }

  return (
    <div className="semantic-analysis">
      <h2>Semantic Analysis</h2>
      <EntitySection title="Topics" entities={analysis.topics} segments={segments} onSeek={onSeek} activeSegmentId={activeSegmentId} />
      <EntitySection title="Problems" entities={analysis.problems} segments={segments} onSeek={onSeek} activeSegmentId={activeSegmentId} />
      <EntitySection title="Questions" entities={analysis.questions} segments={segments} onSeek={onSeek} activeSegmentId={activeSegmentId} />
      <EntitySection title="Solutions" entities={analysis.solutions} segments={segments} onSeek={onSeek} activeSegmentId={activeSegmentId} />
      <EntitySection title="Decisions" entities={analysis.decisions} segments={segments} onSeek={onSeek} activeSegmentId={activeSegmentId} />
      <EntitySection title="Action Items" entities={analysis.action_items} segments={segments} onSeek={onSeek} activeSegmentId={activeSegmentId} />
    </div>
  );
}
