import type { Meeting, TranscriptResponse, SemanticAnalysisResponse } from "../types";

const BASE = "http://localhost:8000/api/v1";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export async function createMeeting(title: string): Promise<Meeting> {
  const res = await fetch(`${BASE}/meetings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return handleResponse<Meeting>(res);
}

export async function getMeeting(id: string): Promise<Meeting> {
  const res = await fetch(`${BASE}/meetings/${id}`);
  return handleResponse<Meeting>(res);
}

export async function uploadAudio(
  meetingId: string,
  file: File
): Promise<Meeting> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/meetings/${meetingId}/audio`, {
    method: "POST",
    body: form,
  });
  return handleResponse<Meeting>(res);
}

export async function startTranscription(
  meetingId: string
): Promise<Meeting> {
  const res = await fetch(`${BASE}/meetings/${meetingId}/transcribe`, {
    method: "POST",
  });
  return handleResponse<Meeting>(res);
}

export async function getTranscript(
  meetingId: string
): Promise<TranscriptResponse> {
  const res = await fetch(`${BASE}/meetings/${meetingId}/transcript`);
  return handleResponse<TranscriptResponse>(res);
}

export function audioUrl(meetingId: string): string {
  return `${BASE}/meetings/${meetingId}/audio`;
}

// V0.3 Semantic Analysis

export async function startSemanticAnalysis(
  meetingId: string
): Promise<Meeting> {
  const res = await fetch(`${BASE}/meetings/${meetingId}/analyze`, {
    method: "POST",
  });
  return handleResponse<Meeting>(res);
}

export async function getSemanticAnalysis(
  meetingId: string
): Promise<SemanticAnalysisResponse> {
  const res = await fetch(`${BASE}/meetings/${meetingId}/analysis`);
  return handleResponse<SemanticAnalysisResponse>(res);
}
