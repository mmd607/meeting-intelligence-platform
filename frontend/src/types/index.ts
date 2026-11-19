export interface Meeting {
  id: string;
  title: string;
  status: MeetingStatus;
  created_at: string;
  updated_at: string;
  language: string | null;
  audio: AudioMeta | null;
  duration: number | null;
  error_message: string | null;
  semantic_analysis_status: string | null;
}

export type MeetingStatus =
  | "CREATED"
  | "UPLOADING"
  | "UPLOADED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export interface AudioMeta {
  original_filename: string | null;
  mime: string | null;
  size_bytes: number | null;
}

export interface TranscriptSegment {
  id: number;
  meeting_id: string;
  start_time: number;
  end_time: number;
  text: string;
  speaker_id: string | null;
}

export interface TranscriptResponse {
  meeting_id: string;
  status: string;
  segments: TranscriptSegment[];
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

// V0.3 Semantic Analysis Types

export interface SemanticEntity {
  id: number;
  description: string;
  segment_ids: number[];
  speaker_id: string | null;
  start_time: number | null;
  end_time: number | null;
}

export interface SemanticAnalysisResponse {
  meeting_id: string;
  status: string | null;
  topics: SemanticEntity[];
  problems: SemanticEntity[];
  questions: SemanticEntity[];
  solutions: SemanticEntity[];
  decisions: SemanticEntity[];
  action_items: SemanticEntity[];
}
