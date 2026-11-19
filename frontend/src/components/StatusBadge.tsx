import type { MeetingStatus } from "../types";

interface Props {
  status: MeetingStatus;
  error?: string | null;
}

const LABELS: Record<MeetingStatus, string> = {
  CREATED: "Created",
  UPLOADING: "Uploading...",
  UPLOADED: "Uploaded",
  PROCESSING: "Processing transcription...",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

export default function StatusBadge({ status, error }: Props) {
  return (
    <div className={`status-badge status-${status.toLowerCase()}`}>
      <span className="dot" />
      <span>{LABELS[status]}</span>
      {error && status === "FAILED" && <span className="error-detail">{error}</span>}
    </div>
  );
}
