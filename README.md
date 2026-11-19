# Meeting Intelligence Platform

Transcription, speaker diarization and source-grounded semantic analysis of meeting audio
(v0.3). Spatial mind mapping is on the roadmap (v0.7), not implemented yet.

## Version 0.3 — Semantic Meeting Analysis

A multimodal meeting intelligence platform. v0.3 adds semantic analysis: after transcription, the system extracts structured information including topics, problems, questions, solutions, decisions, and action items — all grounded to source transcript segments.

v0.1 and v0.2 capabilities are fully preserved.

---

## Current Capabilities (v0.3)

- Create meetings via API or web UI
- Upload audio files (WAV, MP3, M4A)
- Audio validation (format, size, MIME type)
- Local filesystem audio storage
- Speech-to-text transcription (configurable: fake stub or Whisper)
- **Speaker diarization** — anonymous speaker attribution via temporal overlap
- Timestamped transcript generation and persistence
- **Semantic analysis** — extract topics, problems, questions, solutions, decisions, action items
- **Source grounding** — every semantic entity references its source transcript segments
- **Timestamp grounding** — entities carry timestamps derived from source segments
- Interactive transcript with audio playback synchronization
- Click any transcript segment to seek audio to that timestamp
- Click semantic entity source links to jump to the corresponding transcript position
- Processing state visualization (Created → Uploading → Uploaded → Processing → Completed/Failed)
- Structured error handling and responses

## Current Limitations (v0.3)

- Speaker IDs are anonymous only (`speaker_1`, `speaker_2`, ...); no named identification
- No importance scoring or acoustic analysis
- No mind mapping — spatial visualization is planned for future versions
- No real-time transcription — processing is batch-only
- No user authentication — all access is open
- Single-process deployment — no microservices or background workers

---

## Architecture

```
Frontend (React + TypeScript + Vite)
    ↓
REST API (FastAPI, /api/v1)
    ↓
Application Layer (API routes)
    ↓
Domain Layer (Meeting + Transcript + Semantic models, states)
    ↓
Infrastructure Layer (SQLAlchemy + SQLite, LocalStorage, TranscriptionService, DiarizationService, SemanticAnalysisService)
    ↓
Storage / STT Engine / Diarization Engine / LLM Provider
```

Modular monolith designed for future extraction into separate services.

---

## Project Structure

```
Smart Audio/
├── backend/
│   ├── app/
│   │   ├── api/v1/meetings.py        # REST endpoints
│   │   ├── core/
│   │   │   ├── config.py             # Environment-based settings
│   │   │   ├── errors.py             # Structured error handling
│   │   │   └── logging.py            # Centralized logging
│   │   ├── domain/models.py          # Meeting states enum
│   │   ├── infrastructure/
│   │   │   ├── db.py                 # SQLAlchemy ORM models
│   │   │   └── storage.py            # Storage abstraction
│   │   ├── repositories/
│   │   │   └── meeting_repository.py # Data access layer
│   │   ├── schemas/meeting.py        # Pydantic request/response
│   │   ├── services/
│   │   │   ├── audio_validation.py   # Upload validation
│   │   │   ├── transcription/        # Transcription abstraction + impls
│   │   │   ├── diarization/          # Diarization abstraction + impls
│   │   │   └── semantic/             # Semantic analysis abstraction + impls
│   │   └── main.py                   # FastAPI entry point
│   ├── tests/                        # Automated test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/               # React components
│   │   ├── hooks/useAudioPlayer.ts   # Audio playback hook
│   │   ├── pages/MeetingPage.tsx     # Main page
│   │   ├── services/api.ts           # API client
│   │   └── types/index.ts            # TypeScript types
│   └── package.json
├── docs/
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

---

## Environment Configuration

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `MAX_AUDIO_SIZE_MB` | `500` | Maximum upload size in MB |
| `STORAGE_PATH` | `./backend/data` | Local audio storage path |
| `DATABASE_URL` | `sqlite:///./backend/data/app.db` | Database connection string |
| `TRANSCRIPTION_PROVIDER` | `fake` | `fake` (stub) or `whisper` (local Whisper) |
| `TRANSCRIPTION_MODEL` | `tiny` | Whisper model size (tiny/base/small/medium) |
| `DIARIZATION_ENABLED` | `false` | Enable/disable speaker diarization after transcription |
| `DIARIZATION_PROVIDER` | `fake` | `fake` (deterministic stub) or `pyannote` (requires pyannote.audio) |
| `SEMANTIC_ANALYSIS_ENABLED` | `false` | Enable/disable semantic analysis after transcription |
| `SEMANTIC_ANALYSIS_PROVIDER` | `fake` | `fake` (deterministic stub) or `llm` (requires openai package + API key) |
| `LLM_PROVIDER` | `openai` | LLM provider (only needed with `SEMANTIC_ANALYSIS_PROVIDER=llm`) |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name (only needed with `SEMANTIC_ANALYSIS_PROVIDER=llm`) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins |

> Never commit `.env` or any file containing API keys/tokens.

---

## Running the System

### Backend

```bash
cd backend
set PYTHONPATH=..
uvicorn backend.app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm run dev
```

Frontend available at: http://localhost:5173

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/meetings` | Create a meeting |
| `GET` | `/api/v1/meetings/{id}` | Get meeting details |
| `POST` | `/api/v1/meetings/{id}/audio` | Upload audio file |
| `POST` | `/api/v1/meetings/{id}/transcribe` | Start transcription |
| `GET` | `/api/v1/meetings/{id}/transcript` | Get transcript |
| `GET` | `/api/v1/meetings/{id}/audio` | Stream audio file |
| `POST` | `/api/v1/meetings/{id}/analyze` | Start semantic analysis |
| `GET` | `/api/v1/meetings/{id}/analysis` | Get semantic analysis results |
| `GET` | `/health` | Health check |

---

## Supported Audio Formats

| Format | Extension | MIME Type |
|--------|-----------|-----------|
| WAV | `.wav` | `audio/wav`, `audio/x-wav`, `audio/wave` |
| MP3 | `.mp3` | `audio/mpeg`, `audio/mp3` |
| M4A | `.m4a` | `audio/mp4`, `audio/x-m4a`, `audio/m4a` |

Maximum file size: configurable via `MAX_AUDIO_SIZE_MB` (default 500 MB).

---

## Running Tests

From the project root:

```bash
python -m pytest backend/tests
```

Last local run: **71 passed** (Python 3.13, Windows 11, 2026-11-19).

All tests cover:
- Meeting CRUD
- Audio upload (valid, invalid, oversized, empty)
- Transcription workflow (success, failure, missing audio)
- Speaker diarization (unit + integration)
- **Semantic analysis (unit + integration)**
- Transcript retrieval with timestamp and speaker validation
- Unit-level validation and transcription/diarization/semantic service tests

Tests use mocked/fake services — no external API calls required.

---

## Transcription Providers

### Fake (default)

Deterministic stub for development and testing. Returns hardcoded segments instantly.

### Whisper (optional)

Local Whisper-based transcription via `faster-whisper`:

```bash
pip install faster-whisper
```

Set `TRANSCRIPTION_PROVIDER=whisper` in `.env`. Models are downloaded on first use.

---

## Speaker Diarization (v0.2)

After transcription, diarization analyzes the audio to identify anonymous speakers (`speaker_1`, `speaker_2`, ...). Attribution is based on **temporal overlap**: each transcript segment is assigned to the diarization speaker with the strongest overlapping time window.

### Providers

#### Fake (default)

Deterministic stub for development and testing. Returns fixed speaker segments (0–5s: Speaker 1, 5–10s: Speaker 2, 10–15s: Speaker 1). No external dependencies.

#### Pyannote (optional)

Local diarization via `pyannote.audio`:

```bash
pip install pyannote.audio
```

Set `DIARIZATION_ENABLED=true` and `DIARIZATION_PROVIDER=pyannote` in `.env`. The pretrained `pyannote/speaker-diarization-3.1` pipeline is used.

### Configuration

To enable diarization:

```env
DIARIZATION_ENABLED=true
DIARIZATION_PROVIDER=fake
```

### Failure Behavior

If diarization fails, transcription is preserved with `speaker_id = null`. The meeting is still marked `COMPLETED`. No stack traces or sensitive errors are exposed to the client.

---

## Semantic Analysis (v0.3)

After transcription, semantic analysis extracts structured information from the speaker-aware transcript. Every extracted entity references its source transcript segments for explainability.

### Supported Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Topic** | Meaningful discussion themes | "API performance" |
| **Problem** | Explicitly mentioned issues or blockers | "High API response time" |
| **Question** | Explicit questions raised | "What about database indexing?" |
| **Solution** | Proposed solutions | "Caching and database indexing" |
| **Decision** | Explicitly agreed outcomes | "Use caching and database indexing" |
| **Action Item** | Tasks someone committed to doing | "speaker_1 will handle database indexing" |

### Source Grounding

Every semantic entity includes:

- `segment_ids` — IDs of the transcript segments that support it
- `start_time` / `end_time` — timestamps derived from source segments
- `speaker_id` — who said it (if applicable)

### Providers

#### Fake (default)

Deterministic stub for development and testing. When given the canonical 5-segment test fixture (API performance discussion), returns predictable results. For other inputs, returns a generic "Discussion" topic and extracts questions.

#### LLM (optional)

LLM-based analysis via OpenAI API:

```bash
pip install openai
```

Set `SEMANTIC_ANALYSIS_ENABLED=true` and `SEMANTIC_ANALYSIS_PROVIDER=llm` in `.env`. Configure your API key via environment variable:

```bash
export OPENAI_API_KEY=sk-...
```

### Configuration

To enable semantic analysis:

```env
SEMANTIC_ANALYSIS_ENABLED=true
SEMANTIC_ANALYSIS_PROVIDER=fake
```

### Failure Behavior

If semantic analysis fails, the transcript and diarization are preserved. The meeting's `semantic_analysis_status` is set to `FAILED`. The transcript remains fully functional.

---

## Meeting States

```
CREATED → UPLOADING → UPLOADED → PROCESSING → COMPLETED
                                          ↘ FAILED
```

---

## Future Roadmap

| Version | Feature |
|---------|---------|
| v0.4 | Important Moment Detection |
| v0.5 | Prosody / Tone / Highlight Analysis |
| v0.6 | Knowledge Graph Construction |
| v0.7 | Spatial Mind Map |
| v0.8 | Real-Time Processing |
| v0.9 | Meeting Intelligence Agent |
| v1.0 | Complete Product |

---

## License

MIT (see [LICENSE](LICENSE)).

## Author

Mohammad Homaiyan — [@mmd607](https://github.com/mmd607)
