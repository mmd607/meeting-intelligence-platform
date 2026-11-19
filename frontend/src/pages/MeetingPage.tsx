import { useState, useEffect, useCallback } from "react";
import type { Meeting } from "../types";
import { getMeeting, startTranscription, startSemanticAnalysis } from "../services/api";
import MeetingCreate from "../components/MeetingCreate";
import AudioUpload from "../components/AudioUpload";
import TranscriptView from "../components/TranscriptView";
import SemanticAnalysisView from "../components/SemanticAnalysisView";
import StatusBadge from "../components/StatusBadge";

export default function MeetingPage() {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null);
  const [audioSeekTime, setAudioSeekTime] = useState<number | null>(null);

  const refreshMeeting = async (id: string) => {
    const m = await getMeeting(id);
    setMeeting(m);
  };

  useEffect(() => {
    if (meeting?.id) {
      const interval = setInterval(() => {
        if (
          meeting.status === "PROCESSING" ||
          meeting.status === "UPLOADING"
        ) {
          refreshMeeting(meeting.id);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [meeting?.id, meeting?.status]);

  const handleTranscribe = async () => {
    if (!meeting) return;
    setTranscribing(true);
    try {
      const m = await startTranscription(meeting.id);
      setMeeting(m);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setTranscribing(false);
    }
  };

  const handleAnalyze = async () => {
    if (!meeting) return;
    setAnalyzing(true);
    try {
      const m = await startSemanticAnalysis(meeting.id);
      setMeeting(m);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSeekFromAnalysis = useCallback((time: number) => {
    setAudioSeekTime(time);
  }, []);

  if (!meeting) {
    return (
      <div className="app-container">
        <header>
          <h1>Meeting Intelligence</h1>
          <p className="tagline">Audio Upload & Timestamped Transcription</p>
        </header>
        <MeetingCreate onCreated={setMeeting} />
      </div>
    );
  }

  const showUpload =
    ["CREATED", "FAILED"].includes(meeting.status) && !meeting.audio;
  const showTranscribe = meeting.status === "UPLOADED";
  const showTranscript = meeting.status === "COMPLETED";
  const showAnalyze =
    meeting.status === "COMPLETED" &&
    meeting.semantic_analysis_status !== "COMPLETED";
  const showAnalysis =
    meeting.status === "COMPLETED" &&
    meeting.semantic_analysis_status === "COMPLETED";

  return (
    <div className="app-container">
      <header>
        <h1>{meeting.title}</h1>
        <StatusBadge status={meeting.status} error={meeting.error_message} />
      </header>

      {showUpload && (
        <AudioUpload meeting={meeting} onUploaded={setMeeting} />
      )}

      {showTranscribe && (
        <div className="card">
          <h2>Ready to Transcribe</h2>
          <p>Audio uploaded: {meeting.audio?.original_filename}</p>
          <button onClick={handleTranscribe} disabled={transcribing}>
            {transcribing ? "Processing..." : "Start Transcription"}
          </button>
        </div>
      )}

      {meeting.status === "PROCESSING" && (
        <div className="card">
          <div className="spinner" />
          <p>Processing transcription...</p>
        </div>
      )}

      {showTranscript && (
        <TranscriptView
          meetingId={meeting.id}
          onSeek={handleSeekFromAnalysis}
          audioSeekTime={audioSeekTime}
          onActiveSegmentChange={setActiveSegmentId}
        />
      )}

      {showAnalyze && (
        <div className="card">
          <h2>Semantic Analysis</h2>
          <p>Transcript ready. Extract topics, problems, decisions, and action items.</p>
          <button onClick={handleAnalyze} disabled={analyzing}>
            {analyzing ? "Analyzing..." : "Start Analysis"}
          </button>
        </div>
      )}

      {meeting.semantic_analysis_status === "PROCESSING" && (
        <div className="card">
          <div className="spinner" />
          <p>Running semantic analysis...</p>
        </div>
      )}

      {showAnalysis && (
        <SemanticAnalysisView
          meetingId={meeting.id}
          onSeek={handleSeekFromAnalysis}
          activeSegmentId={activeSegmentId}
        />
      )}

      <button className="back-btn" onClick={() => setMeeting(null)}>
        New Meeting
      </button>
    </div>
  );
}
