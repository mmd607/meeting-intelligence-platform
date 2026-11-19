import { useState, useEffect } from "react";
import type { TranscriptSegment } from "../types";
import { getTranscript } from "../services/api";
import AudioPlayer from "./AudioPlayer";
import { useAudioPlayer } from "../hooks/useAudioPlayer";

interface Props {
  meetingId: string;
  onSeek?: (time: number) => void;
  audioSeekTime?: number | null;
  onActiveSegmentChange?: (id: number | null) => void;
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

export default function TranscriptView({
  meetingId,
  audioSeekTime,
  onActiveSegmentChange,
}: Props) {
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { initAudio, currentTime, duration, playing, toggle, seek } =
    useAudioPlayer();

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getTranscript(meetingId);
        if (!cancelled) setSegments(data.segments);
      } catch (err: any) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  useEffect(() => {
    if (segments.length === 0) return;
    const active = segments.find(
      (s) => currentTime >= s.start_time && currentTime < s.end_time
    );
    if (active) {
      setActiveId(active.id);
      onActiveSegmentChange?.(active.id);
    }
  }, [currentTime, segments, onActiveSegmentChange]);

  // Handle external seek requests (from semantic analysis clicks)
  useEffect(() => {
    if (audioSeekTime !== null && audioSeekTime !== undefined) {
      seek(audioSeekTime);
      if (!playing) toggle();
    }
  }, [audioSeekTime]);

  const handleSegmentClick = (seg: TranscriptSegment) => {
    seek(seg.start_time);
    if (!playing) toggle();
  };

  if (loading) return <div className="card">Loading transcript...</div>;
  if (error) return <div className="card error">{error}</div>;

  return (
    <div className="transcript-container">
      <AudioPlayer meetingId={meetingId} onReady={initAudio} />

      <div className="audio-controls">
        <button onClick={toggle}>{playing ? "Pause" : "Play"}</button>
        <span className="time-display">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>

      <div className="transcript">
        {segments.length === 0 ? (
          <p className="empty">No transcript segments found.</p>
        ) : (
          segments.map((seg) => (
            <div
              key={seg.id}
              className={`segment ${activeId === seg.id ? "active" : ""}`}
              onClick={() => handleSegmentClick(seg)}
            >
              <span className="timestamp">{formatTime(seg.start_time)}</span>
              {seg.speaker_id && (
                <span className="speaker-label">
                  {speakerLabel(seg.speaker_id)}
                </span>
              )}
              <span className="text">{seg.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
