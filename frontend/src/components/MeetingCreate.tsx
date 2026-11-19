import { useState } from "react";
import type { Meeting } from "../types";
import { createMeeting } from "../services/api";

interface Props {
  onCreated: (meeting: Meeting) => void;
}

export default function MeetingCreate({ onCreated }: Props) {
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const meeting = await createMeeting(title || "Untitled meeting");
      onCreated(meeting);
    } catch (err: any) {
      setError(err.message ?? "Failed to create meeting");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Create a Meeting</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Meeting title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Creating..." : "Create Meeting"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
