import { useEffect, useRef } from "react";
import { audioUrl } from "../services/api";

interface Props {
  meetingId: string;
  onReady: (el: HTMLAudioElement) => void;
}

export default function AudioPlayer({ meetingId, onReady }: Props) {
  const ref = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (ref.current) onReady(ref.current);
  }, [meetingId, onReady]);

  return (
    <div className="audio-player">
      <audio ref={ref} controls src={audioUrl(meetingId)} preload="metadata" />
    </div>
  );
}
