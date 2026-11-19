import { useCallback, useRef, useState } from "react";
import type { Meeting } from "../types";
import { uploadAudio } from "../services/api";

interface Props {
  meeting: Meeting;
  onUploaded: (meeting: Meeting) => void;
}

const ACCEPTED = ".wav,.mp3,.m4a";

export default function AudioUpload({ meeting, onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    setError(null);
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (![".wav", ".mp3", ".m4a"].includes(ext)) {
      setError("Unsupported format. Use .wav, .mp3, or .m4a");
      return;
    }
    if (f.size > 500 * 1024 * 1024) {
      setError("File exceeds 500 MB limit");
      return;
    }
    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const onUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setError(null);
    try {
      const interval = setInterval(() => setProgress((p) => Math.min(p + 10, 90)), 200);
      const meeting2 = await uploadAudio(meeting.id, file);
      clearInterval(interval);
      setProgress(100);
      onUploaded(meeting2);
    } catch (err: any) {
      setError(err.message ?? "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="card">
      <h2>Upload Audio</h2>
      <p className="subtitle">Meeting: {meeting.title}</p>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        {file ? (
          <div className="file-info">
            <span className="file-name">{file.name}</span>
            <span className="file-size">{formatSize(file.size)}</span>
          </div>
        ) : (
          <span>Drag & drop an audio file or click to browse</span>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {file && (
        <div className="upload-actions">
          <button onClick={onUpload} disabled={uploading}>
            {uploading ? `Uploading... ${progress}%` : "Upload"}
          </button>
          {!uploading && (
            <button className="secondary" onClick={() => { setFile(null); setError(null); }}>
              Clear
            </button>
          )}
        </div>
      )}

      {uploading && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}
