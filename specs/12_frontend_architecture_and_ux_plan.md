# SPEC 12 - Frontend Architecture and UX Plan

Status: ✅ Implemented (Streamlit MVP)
Date Updated: 2026-03-17
Scope: Guest-mode MVP frontend — Streamlit single-file app

---

## 1. Decision: Streamlit (not Next.js)

The original plan called for a Next.js 14 App Router frontend. After MVP assessment, the frontend was implemented as a **Streamlit single-file app** (`frontend_streamlit/app.py`).

**Rationale:**
- No separate build pipeline (no npm, TypeScript, bundler)
- Full Python stack — same language as backend
- Rapid iteration on layout and state without component boilerplate
- Native support for metrics, charts, progress bars, and file upload
- Custom CSS injected via `st.markdown(unsafe_allow_html=True)` for styled UI
- Works directly with the FastAPI backend via `requests`

The Next.js architecture remains documented as the target for a future web-quality frontend (Phase FE).

---

## 2. Current Implementation: Streamlit App

### File
```
frontend_streamlit/
├── app.py                    ← Single-file Streamlit application
└── .streamlit/
    └── config.toml           ← Light theme base + server config
```

### config.toml
```toml
[theme]
base = "light"
primaryColor = "#0D9488"
backgroundColor = "#F7F7F2"
secondaryBackgroundColor = "#EFEDE3"
textColor = "#1C1917"
font = "sans serif"

[server]
headless = true
```

---

## 3. App Structure (`app.py`)

### State (`ensure_state`)
All state lives in `st.session_state`. Initialized once at startup:

| Key | Type | Purpose |
|-----|------|---------|
| `backend_url` | str | FastAPI base URL (default: `http://127.0.0.1:8000`) |
| `guest_id` | str (UUID4) | Unique guest identifier, persists across reruns |
| `resume_id` | int \| None | DB ID of the uploaded resume |
| `resume_data` | dict \| None | Parsed CV data (skills, projects) from upload response |
| `session_id` | int \| None | Active interview session ID |
| `interview_type` | str | `technical` \| `system_design` \| `behavioral` \| `resume` |
| `messages` | list[dict] | Full conversation history (role, content, evaluation, question_number) |
| `started` | bool | Whether the interview session has started |
| `session_complete` | bool | Whether all questions have been answered |
| `last_evaluation` | dict \| None | Most recent per-answer evaluation |
| `last_report` | dict \| None | Final report payload |
| `max_questions` | int | Fixed at 8 |
| `resume_chunks_embedded` | bool | Whether background CV embedding has completed |

### Rendering Flow

```
main()
  ├── set_page_config()
  ├── ensure_state()
  ├── inject_styles()          ← CSS overrides for professional light theme
  ├── render_header()          ← App title + "New Interview" reset button
  │
  ├── columns([left, right])
  │   ├── resume_step()        ← Step 1: Upload CV, show skills/projects
  │   └── setup_session_step() ← Step 2: Pick interview type, start session
  │
  ├── interview_step()         ← Step 3: Q/A chat timeline + chat_input
  └── report_step()            ← Step 4: Fetch and display final report
```

---

## 4. User Flow

### Happy Path

1. Open app → `ensure_state()` generates a `guest_id`
2. Upload PDF → `POST /api/resume/upload` → receive resume_id + parsed skills/projects
3. Background embedding starts automatically (FastAPI `BackgroundTasks`)
4. User sees "Embedding in background..." + Refresh button
5. Select interview type → click "Create Session" → `POST /api/session/`
6. App calls `GET /api/session/{id}/start` → receives first AI question
7. User types answer in chat input → `POST /api/session/{id}/message`
8. App shows evaluation scores inline (score pills + feedback box)
9. Loop until 8 questions answered → `session_complete = True`
10. Click "Fetch Report" → `GET /api/report/{id}` → renders full report

### Error Recovery

- **Upload timeout:** App auto-calls `GET /api/resume/guest/{guest_id}` to recover
- **API errors:** Shown inline with `st.error()` — no page crash
- **Re-upload:** Old ChromaDB chunks are deleted before new ones are inserted
- **New Interview:** "↺ New Interview" button resets state, keeps `guest_id`

---

## 5. Backend API Mapping

Base URL: `http://127.0.0.1:8000` (configured in `st.session_state.backend_url`)

### Resume
- `POST /api/resume/upload?guest_id=...` → upload PDF, returns resume_id + parsed data
- `GET /api/resume/guest/{guest_id}` → fetch latest resume (timeout recovery)
- `GET /api/resume/{resume_id}/status` → check embedding progress (`chunks_embedded`)

### Session
- `POST /api/session/` → create session with guest_id, interview_type, resume_id
- `GET /api/session/{session_id}/start` → generate first AI question
- `POST /api/session/{session_id}/message` → submit answer, returns next question + evaluation
- `POST /api/session/{session_id}/end` → mark session complete

### Report
- `GET /api/report/{session_id}` → compiled report
- `GET /api/report/{session_id}?regenerate=true` → force regeneration

### Unified Error Contract (handled globally in `parse_api_error`)
```json
{
  "detail": {
    "error": {
      "code": "STRING_ERROR_CODE",
      "message": "Human-readable message",
      "context": {}
    }
  }
}
```

---

## 6. Visual Design System

### Color Palette
| Role | Value | Usage |
|------|-------|-------|
| Background | `#f6f4ee` (warm ivory) | App base |
| Panel | `#fffdf8` (cream white) | Cards/step cards |
| Border | `#e7e3d5` | Card borders, dividers |
| Ink | `#111827` | Headings and primary text |
| Ink soft | `#4b5563` | Secondary/label text |
| Accent teal | `#0f766e` | Questions, active accents |
| Accent indigo | `#6366F1` | Buttons, step wizard active |
| Success green | `#d1fae5` / `#0d7d56` | Positive scores, score-high pills |
| Warning amber | `#fef3c7` / `#92400e` | Mid scores |
| Error red | `#fee2e2` / `#dc2626` | Low scores, errors |

### Typography
- Headings: `Fraunces` (serif, display) — via Google Fonts
- Body/UI: `Space Grotesk` (geometric sans) — via Google Fonts

### Component Classes (via injected CSS)

| Class | Description |
|-------|-------------|
| `.hero` | App header bar — white card with shadow |
| `.step-card` | Section container card |
| `.turn-card` | Q/A conversation turn container |
| `.turn-q` | AI question bubble (teal left border) |
| `.turn-a` | User answer bubble (blue left border) |
| `.eval-card` | Score/evaluation block |
| `.report-card` | Final report container |
| `.chip` | Skill tag pill |

---

## 7. Message Format in Session State

Each message in `st.session_state.messages` is a dict:

**AI message:**
```python
{
    "role": "assistant",
    "content": "Why did you choose PostgreSQL for that project?",
    "question_number": 3
}
```

**User message (after evaluation):**
```python
{
    "role": "user",
    "content": "I chose PostgreSQL because...",
    "answered_question_number": 3,
    "evaluation": {
        "technical_correctness": 7,
        "depth_of_explanation": 6,
        "clarity": 8,
        "overall_score": 7,
        "strengths": ["Clear reasoning"],
        "weaknesses": ["Missed trade-offs"],
        "suggestions": ["Compare with MongoDB trade-offs"]
    }
}
```

`_build_turns()` pairs messages by `question_number` ↔ `answered_question_number` to build the display timeline.

---

## 8. Running the Frontend

### Local
```bash
cd frontend_streamlit
streamlit run app.py
```
Opens at `http://localhost:8501`

### With Docker (backend via docker-compose)
```bash
# Start backend
docker-compose up --build

# Start frontend separately (Streamlit is not containerized yet)
cd frontend_streamlit
pip install streamlit pandas requests
streamlit run app.py
```

### Dependencies
No separate `requirements.txt` needed — the frontend only uses:
- `streamlit`
- `pandas` (for bar chart in report)
- `requests` (for API calls)

These are standard installs: `pip install streamlit pandas requests`

---

## 9. Future Next.js Frontend (Phase FE — Deferred)

The original Next.js architecture remains the target for production:

**Tech Stack:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Zustand for state
- Axios for API client

**Routes:**
- `/` — Landing with CTA
- `/dashboard` — Resume upload + interview type selection
- `/interview/[sessionId]` — Live chat
- `/report/[sessionId]` — Score + feedback

**When to build it:**
- When the MVP is validated with real users
- When streaming token-by-token LLM output is needed (not possible in Streamlit)
- When mobile UX and custom animations are required

---

## 10. Acceptance Criteria (Current Streamlit MVP)

Functional:
- Upload → session → interview → report works end-to-end as guest ✅
- Background embedding doesn't block session creation ✅
- All 4 interview types work ✅
- Report shows overall score, per-question bars, strengths/weaknesses/suggestions ✅
- "New Interview" resets cleanly without generating a new guest_id ✅

UX:
- Clear loading states during API calls ✅
- Score pills color-coded by performance level ✅
- Feedback shown inline after each answer ✅
- Interview type clearly configurable before start ✅

Resilience:
- Upload timeout → auto-recovery via guest lookup ✅
- API error shown inline without crash ✅
- Re-upload deletes stale ChromaDB chunks ✅
