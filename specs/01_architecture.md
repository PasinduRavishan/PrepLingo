# SPEC 01 — System Architecture

**Status:** Draft — Pending Tech Stack Decisions

---

## Architecture Overview (Intentionally Simple)

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Next.js)                     │
│   Landing → Dashboard → Interview Chat → Report Page     │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTP / REST
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│   /auth     /resume    /session     /report              │
│                                                          │
│             Service Layer                                │
│   ResumeService  SessionService  EvalService             │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              LangChain Layer (AI Core)                   │
│                                                          │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  Question Chain │    │    Evaluation Chain          │ │
│  │  (LCEL)         │    │    (LCEL + Pydantic Parser)  │ │
│  └────────┬────────┘    └──────────────┬──────────────┘ │
│           │                            │                  │
│  ┌────────▼────────────────────────────▼──────────────┐ │
│  │            Retriever (Vector Store)                 │ │
│  │   Resume Chunks  +  Domain Knowledge Chunks         │ │
│  └────────────────────────────────────────────────────┘ │
│                       │                                  │
│              ┌────────▼───────┐                          │
│              │   LLM Provider │                          │
│              │  (OpenAI/etc.) │                          │
│              └────────────────┘                          │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Data Layer                             │
│                                                          │
│   SQLite/PostgreSQL         Vector Store                 │
│   (Users, Sessions,         (FAISS / ChromaDB)           │
│    Messages, Reports)       (Document embeddings)        │
└─────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Frontend (Next.js)
- Landing page (introduction + CTA)
- Dashboard (resume upload + interview type selection)
- Interview page (real-time chat interface with AI)
- Report page (score breakdown + feedback)

### Backend (FastAPI)
- REST API — all endpoints
- Auth middleware (JWT validation)
- Resume parsing service (PDF → structured JSON)
- Session orchestration (create, chat, end)
- Report compilation
- **Does NOT contain LangChain logic directly** — delegates to LangChain Layer

### LangChain Layer (Python, within backend)
- All LLM interactions go through here
- Manages chains, prompts, memory, retrievers
- Two main chains:
  - `QuestionChain`: retrieves context → generates next question
  - `EvaluationChain`: evaluates user answer → returns structured scores

### Vector Store
- Stores two types of embeddings:
  1. **Domain knowledge** (pre-ingested, static per interview type)
  2. **User resume chunks** (dynamic, per user session)
- Retriever fetches top-K most relevant chunks at query time

### Database (SQL)
- User accounts
- Interview sessions (state, type, timestamps)
- Messages (question/answer pairs)
- Evaluations (per-answer scores)
- Reports (aggregated session summary)

---

## Request Lifecycle — Interview Message

```
User types an answer in the chat
    ↓
POST /api/session/{id}/message  {content: "..."}
    ↓
SessionService.process_message()
    ↓
LangChain QuestionChain:
    1. Load conversation memory (last N messages)
    2. Retrieve: Vector Store → top-K relevant chunks
       (resume chunks + domain knowledge chunks)
    3. Build prompt: [system_prompt + context + history + user_message]
    4. Call LLM → get next question
    ↓
LangChain EvaluationChain (runs parallel or sequential):
    1. Same context
    2. Evaluate user's answer → structured JSON
       {score, strengths, weaknesses, suggestions}
    ↓
Save message + evaluation to DB
    ↓
Return: {ai_question, evaluation} to frontend
```

---

## Two Separate Vector Namespaces / Collections

```
VectorStore
├── resume_store/
│   └── user_{user_id}/          ← per user, loaded on resume upload
│       └── [resume chunks]
│
└── knowledge_store/
    ├── technical/               ← pre-ingested domain docs
    ├── system_design/
    ├── behavioral/
    └── resume_interview/        ← general interview tips
```

At interview time, the retriever queries BOTH:
- The user's resume store → for personalization
- The relevant domain knowledge store → for grounding

---

## Environment

| Component | Local Dev | Notes |
|---|---|---|
| Backend | `uvicorn app.main:app --reload` | Port 8000 |
| Frontend | `npm run dev` | Port 3000 |
| Vector Store | Local file (FAISS) | No cloud needed for dev |
| Database | SQLite file | No setup needed for dev |
| LLM | API key in .env | OpenAI / Gemini |

---

## What Stays Simple (By Design)

- No microservices — single FastAPI monolith
- No message queue — synchronous request/response
- No cloud deployment required — runs 100% locally
- No streaming responses (v1) — can add later
- Single user vector namespace — no multi-tenancy complexity
