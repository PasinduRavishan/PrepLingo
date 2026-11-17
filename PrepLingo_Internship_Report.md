# PrepLingo — AI Interview Trainer
## Internship Final Report

**Prepared by:** Pasindu Ravishan  
**Email:** pasinduravishan.22@cse.mrt.ac.lk  
**Project:** PrepLingo — AI-Powered Mock Interview Platform  
**Period:** March 2026  
**Repository:** `PrepLingo/` (GitHub)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Vision and Purpose](#2-project-vision-and-purpose)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Core AI Design — RAG Pipeline](#5-core-ai-design--rag-pipeline)
6. [Data Models](#6-data-models)
7. [LangChain Layer — AI Orchestration](#7-langchain-layer--ai-orchestration)
8. [Backend Implementation — FastAPI](#8-backend-implementation--fastapi)
9. [Frontend Implementation — Streamlit](#9-frontend-implementation--streamlit)
10. [Knowledge Base and Ingestion Pipeline](#10-knowledge-base-and-ingestion-pipeline)
11. [Implementation Phases and Timeline](#11-implementation-phases-and-timeline)
12. [Production Deployment — GCP](#12-production-deployment--gcp)
13. [Testing and Quality Assurance](#13-testing-and-quality-assurance)
14. [Key Engineering Challenges and Solutions](#14-key-engineering-challenges-and-solutions)
15. [Future Roadmap — Voice Upgrade](#15-future-roadmap--voice-upgrade)
16. [Key Decisions and Rationale](#17-key-decisions-and-rationale)
17. [Learning Outcomes](#18-learning-outcomes)

---

## 1. Executive Summary

PrepLingo is a web-based AI interview simulator built during an internship period. The platform conducts realistic mock interviews using a candidate's own resume as a primary knowledge source, combined with curated domain-specific knowledge bases. Every interview interaction is powered by Retrieval-Augmented Generation (RAG), meaning the AI grounds every question and evaluation in real, retrieved knowledge rather than relying on hallucinations.

The system was built end-to-end — from architecture design and data modelling through backend API implementation, AI pipeline construction, frontend development, and full production deployment on Google Cloud Platform. The final product is a fully containerised, live-running application that any user can access as a guest (no registration required), upload their resume, select an interview type, conduct a full 8-question mock interview, and receive a detailed performance report.

**Key outcomes:**
- Four interview types supported: Resume-Based, Technical, System Design, Behavioral
- Full LangChain LCEL pipeline with dual-source RAG retrieval
- Local HuggingFace embedding model eliminating API dependency for vectors
- Groq LLM (Llama 3.3 70B) with automatic fallback to 8B model
- Three-container Docker Compose deployment (FastAPI + Streamlit + Nginx) on GCP e2-medium
- Comprehensive automated test suite covering all phases
- Professional Streamlit frontend with light theme, score pills, and bar chart reports

---

## 2. Project Vision and Purpose

### The Problem

Job candidates preparing for technical interviews lack access to realistic, personalised practice. Generic question banks do not adapt to the candidate's specific background. Human mock interviewers are expensive and unavailable on demand. Existing AI chatbots give generic responses not grounded in the candidate's own resume.

### The Solution

PrepLingo bridges this gap by combining three capabilities:

1. **Resume Intelligence:** The candidate uploads their CV. The system parses and embeds it as a structured knowledge source, enabling the AI to ask about specific projects, technologies, and experiences the candidate has actually had.

2. **Domain Knowledge Grounding:** Curated knowledge bases covering CS fundamentals, system design patterns, STAR behavioral frameworks, and interview coaching guides are pre-embedded in a vector store. Every AI question is grounded in this domain expertise.

3. **Real-time Evaluation:** After every answer, a structured evaluation chain scores the response across three dimensions (technical correctness, depth of explanation, clarity) and provides actionable strengths, weaknesses, and suggestions — immediately, not at the end.

### Four Interview Types

| Type | Primary Knowledge Source | CV Role |
|------|--------------------------|---------|
| **Resume-Based** | User's CV (primary) | The knowledge base itself |
| **Technical** | CS/Engineering concepts DB | Filters topics by CV skills |
| **System Design** | Architecture & design patterns DB | Anchors problems to CV projects |
| **Behavioral** | STAR framework & behavioral guides | Pulls project stories from CV |

### Non-Goals (Explicit Scope Boundaries)

- No voice interviews (planned as future Phase 1 upgrade — see Section 15)
- No payment system or subscriptions
- No real company interview simulation
- Authentication deferred to post-MVP phase (guest mode used throughout)

---

## 3. System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   Browser / User                              │
│                 (Streamlit Frontend)                          │
│   Resume Upload → Interview Chat → Report Page               │
└───────────────────────┬──────────────────────────────────────┘
                        │  HTTP / REST
┌───────────────────────▼──────────────────────────────────────┐
│                   FastAPI Backend                             │
│                                                              │
│   /api/auth  /api/resume  /api/session  /api/report          │
│                                                              │
│              Service Layer                                   │
│   ResumeService   SessionService   ReportService            │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│              LangChain Layer (AI Core)                       │
│                                                              │
│   ┌──────────────────┐    ┌─────────────────────────────┐   │
│   │  QuestionChain   │    │    EvaluationChain           │   │
│   │  (LCEL)          │    │    (LCEL + JsonOutputParser)  │   │
│   └────────┬─────────┘    └──────────────┬──────────────┘   │
│            │                             │                   │
│   ┌────────▼─────────────────────────────▼──────────────┐   │
│   │           DualRetriever (ChromaDB)                  │   │
│   │   Resume Chunks  +  Domain Knowledge Chunks          │   │
│   └─────────────────────────────────────────────────────┘   │
│                        │                                     │
│               ┌────────▼───────┐                             │
│               │   Groq LLM     │                             │
│               │ Llama 3.3 70B  │                             │
│               └────────────────┘                             │
└──────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                     Data Layer                               │
│                                                              │
│   SQLite (SQLModel ORM)          ChromaDB (Vector Store)     │
│   - GuestUsers                   - resume_store/             │
│   - InterviewSessions              [per user resume chunks]  │
│   - Messages                     - knowledge_store/          │
│   - Evaluations                    [domain knowledge chunks] │
│   - Reports                                                  │
│   - Resumes                                                  │
└──────────────────────────────────────────────────────────────┘
```

### Production Deployment Architecture (GCP)

```
Internet
    │
    ▼ :80
┌──────────────────────────────────────────────────────────────┐
│  GCP Compute Engine VM  (e2-medium, 2 vCPU / 4 GB RAM)       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  nginx:1.25 (container, port 80)                     │    │
│  │  /api/*  → backend:8000 (internal Docker network)    │    │
│  │  /*      → frontend:8501 (internal Docker network)   │    │
│  └──────────────────────────────────────────────────────┘    │
│            │                          │                      │
│  ┌─────────▼──────────┐  ┌────────────▼───────────────┐     │
│  │  backend:8000      │  │  frontend:8501              │     │
│  │  FastAPI + LangChain│  │  Streamlit                 │     │
│  │  ChromaDB          │  │  calls backend via          │     │
│  │  BAAI embedding    │  │  internal Docker network    │     │
│  └────────────────────┘  └────────────────────────────┘     │
│                                                              │
│  Named Docker Volumes:                                       │
│  embedding-cache → /root/.cache/huggingface (BAAI model)    │
│  vector-data     → ChromaDB index                            │
│  db-data         → SQLite database                           │
└──────────────────────────────────────────────────────────────┘
```

### Interview Message Lifecycle

```
User types an answer in the chat
    ↓
POST /api/session/{id}/message  { content: "user answer..." }
    ↓
SessionService.process_message()
    ↓
  asyncio.gather():
    ├── EvaluationChain:
    │     1. Load conversation history (WindowMemory, k=6)
    │     2. DualRetriever → top-K relevant chunks
    │     3. Evaluate answer → structured JSON scores
    │
    └── QuestionChain:
          1. Same context + history
          2. Generate next interview question
    ↓
Save Message + Evaluation to SQLite DB
    ↓
Update ConversationBufferWindowMemory
    ↓
Return { ai_question, evaluation, question_number, session_complete }
    ↓
Frontend renders question + score pills + feedback
```

---

## 4. Technology Stack

### Backend

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Web Framework | **FastAPI** | Python 3.11+ | Async-native, auto OpenAPI docs, Pydantic-first |
| AI Orchestration | **LangChain LCEL** | — | Modern chain composition, full learning value |
| LLM Provider | **Groq** (`llama-3.3-70b-versatile`) | — | LPU hardware = near-instant inference, no quota issues |
| LLM Fallback | **Groq** (`llama-3.1-8b-instant`) | — | Automatic via `with_fallbacks()` on HTTP 429 |
| Embeddings | **BAAI/bge-base-en-v1.5** (local) | 768 dims | MTEB 72.3, no API key, no rate limits, no cold-start |
| Vector Store | **ChromaDB** | — | Persistent, metadata filtering, LangChain native |
| PDF Parsing | **PyMuPDF (fitz)** | — | Fast, reliable Python-native PDF extraction |
| ORM | **SQLModel** | — | Pydantic models = DB models (FastAPI native) |
| Database | **SQLite** (dev/prod) | — | Zero setup; volume-persisted in Docker |
| Server | **Uvicorn** | — | ASGI server for FastAPI |

### Frontend

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | **Streamlit** | Single-file Python app, no build pipeline, rapid iteration |
| HTTP Client | **requests** | Calls FastAPI backend directly |
| Charts | **pandas + st.bar_chart** | Score visualization in final report |
| Styling | Custom CSS via `st.markdown` | Professional light theme |

### Infrastructure

| Component | Tool |
|-----------|------|
| Containerization | Docker multi-stage build + Docker Compose v2 |
| Reverse Proxy | Nginx 1.25 (WebSocket + API routing) |
| Cloud | GCP Compute Engine e2-medium VM |
| Version Control | Git + GitHub |
| API Docs | FastAPI auto-generated Swagger at `/docs` |
| Env Vars | `.env` via pydantic-settings |

### Why Groq over Gemini/OpenAI

After encountering daily quota exhaustion on Gemini's free tier during Phase 2 development, the team switched to Groq for all LLM inference. Groq's LPU (Language Processing Unit) hardware delivers near-instant text generation (~0.5s for 8B, ~2-4s for 70B), making the interview feel like a real-time conversation. The free developer tier offers 14,400 requests/day — far more than enough for an interview platform.

### Why BAAI/bge-base-en-v1.5 over API Embeddings

During Phase 5 hardening, a critical issue emerged: two concurrent operations (background CV embedding + DualRetriever query embedding) both called the Google Embedding API simultaneously, causing 25-second timeouts after the first answer. The solution was switching to a local HuggingFace model (`BAAI/bge-base-en-v1.5`). This model:
- Runs entirely locally — zero API calls, zero rate limits
- Scores 72.3 on the MTEB benchmark (vs Gemini embedding-001's ~71.0)
- Produces 768-dimensional vectors (same shape)
- Is pre-downloaded into the Docker image at build time — zero cold-start

---

## 5. Core AI Design — RAG Pipeline

### The Core Principle

Every AI turn in PrepLingo retrieves from **two sources simultaneously**:

```
At every AI turn:
  RETRIEVE from:
  ├── [1] User's Resume Chunks     → personalization, CV-specific context
  └── [2] Domain Knowledge Chunks  → grounded, accurate interview content

  COMBINE into prompt → LLM generates next question / evaluation
```

This means every question is grounded in both what the user knows (from their resume) AND what real interview guides say about that topic.

### Phase A — Knowledge Base Ingestion (One-Time Setup)

```
Raw Documents (PDF, .md, .txt, .html, .docx)
        ↓
Document Loaders  [PyMuPDF, TextLoader, HTMLParser, DocxParser]
        ↓
RecursiveCharacterTextSplitter (chunk_size=800, overlap=100)
        ↓
BAAI/bge-base-en-v1.5 Embedding Model (local HuggingFace)
        ↓
ChromaDB — knowledge_store collection
  Metadata: { source, interview_type, topic, content_hash }
```

**Knowledge base taxonomy:**
```
backend/knowledge_base/
├── technical/       (databases, backend concepts, data structures, networking, Python/JS)
├── system_design/   (caching, load balancing, case studies: URL shortener, messaging)
├── behavioral/      (STAR method, common questions, soft skills, leadership principles)
└── resume_interview/ (project question banks, trade-off prompts, tech-stack deep-dives)
```

### Phase B — Resume Ingestion (Per User Upload)

The resume pipeline transforms a PDF into structured semantic chunks:

```
PDF Upload
    ↓ PyMuPDF → raw text extraction
    ↓ LLM (Groq) + JsonOutputParser → structured JSON
      { name, skills, projects[{name, description, tech_stack, outcomes}],
        experience, education }
    ↓ SQLite → Resume row (raw_text + parsed_json)
    ↓ Semantic chunk building:
        [1] Identity + Core Skills chunk
        [2] One chunk per project  ← most important for context
        [3] Work Experience narrative
        [4] Education & Certifications
    ↓ ChromaDB → resume_store collection
      Metadata: { guest_id, source: "resume", interview_type: "resume" }
```

**Why structured chunks over raw text splitting?**  
Raw splitting loses section context — a skills sentence could land mid-chunk with unrelated content. Structured chunks ensure each project is a self-contained unit, making retrieval precise: asking about "your blockchain project" retrieves the exact project chunk.

**Stale chunk deletion:** Before inserting new embeddings, old chunks for the same `guest_id` are deleted from ChromaDB. This prevents duplication when a user re-uploads their resume.

### Phase C — Dual Retrieval at Interview Time

```python
# Pseudocode for DualRetriever
def build_dual_retriever(guest_id: str, interview_type: str):
    resume_retriever = chroma_resume_store.as_retriever(
        search_kwargs={"filter": {"guest_id": guest_id}, "k": 2}
    )
    knowledge_retriever = chroma_knowledge_store.as_retriever(
        search_kwargs={"filter": {"interview_type": interview_type}, "k": 3}
    )
    return MergerRetriever(retrievers=[resume_retriever, knowledge_retriever])
```

**Why 2 resume + 3 knowledge?**  
Resume chunks provide personalisation (WHO/WHAT context). Knowledge chunks provide grounding (WHAT IS GOOD). Domain correctness matters more for evaluation quality, hence 3 knowledge chunks.

### ChromaDB Two-Namespace Design

```
ChromaDB
├── resume_store/
│   └── per user, filtered by guest_id
│       └── [structured resume chunks]
│
└── knowledge_store/
    ├── technical/
    ├── system_design/
    ├── behavioral/
    └── resume_interview/
```

---

## 6. Data Models

All database models use **SQLModel** — combining Pydantic validation with SQLAlchemy ORM.

### Entity Relationship Diagram

```
GuestUser (1) ──────── (many) Resume
                               │
                               │ (optional link)
GuestUser (1) ──────── (many) InterviewSession
                               │
                     ┌─────────┴─────────┐
                     │                   │
              (many) Message      (many) Evaluation
                                         │
                               (one)    Report
```

### Table: `guest_users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `guest_id` | VARCHAR UNIQUE | UUID generated in browser localStorage |
| `name` | VARCHAR | Optional |
| `created_at` | DATETIME | Auto-set |

**Design note:** The guest_id pattern enables a completely auth-free user experience. The browser generates a UUID once, stores it in localStorage, and sends it with every request. No email or password required.

### Table: `resumes`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `guest_id` | VARCHAR INDEX | Links to guest user |
| `raw_text` | TEXT | Full PDF text |
| `parsed_data` | TEXT | JSON: `{ name, skills, projects, experience, education }` |
| `chunks_embedded` | BOOLEAN | Whether resume is in ChromaDB |
| `created_at` | DATETIME | Upload time |

### Table: `interview_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `guest_id` | VARCHAR INDEX | Session owner |
| `interview_type` | ENUM | `resume / technical / system_design / behavioral` |
| `status` | ENUM | `in_progress / completed` |
| `question_count` | INTEGER | Current question number (0–8) |
| `max_questions` | INTEGER | Default 8 |
| `resume_id` | INTEGER FK | Required for resume-mode, optional otherwise |
| `created_at` | DATETIME | Session start |
| `ended_at` | DATETIME | Session end (null if in_progress) |

### Table: `messages`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK | Which session |
| `role` | ENUM | `ai / user` |
| `content` | TEXT | Question or answer text |
| `question_number` | INTEGER | Null for user, 1–8 for AI messages |
| `ai_question_asked` | TEXT | Denormalised: the question paired with this user answer |
| `created_at` | DATETIME | Timestamp |

**Design note:** `ai_question_asked` is stored on the user message row. The EvaluationChain needs both the question AND the answer together. Storing it denormalised avoids a join and ensures evaluation always has the correct pair even if history gets complex.

### Table: `evaluations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK INDEX | Which session |
| `message_id` | INTEGER FK | Which user answer |
| `question_number` | INTEGER | 1–8 |
| `technical_correctness` | INTEGER | 0–10 |
| `depth_of_explanation` | INTEGER | 0–10 |
| `clarity` | INTEGER | 0–10 |
| `overall_score` | INTEGER | 0–10 (weighted average) |
| `strengths` | TEXT | JSON array |
| `weaknesses` | TEXT | JSON array |
| `suggestions` | TEXT | JSON array |
| `created_at` | DATETIME | Evaluation time |

### Table: `reports`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK UNIQUE | One report per session |
| `interview_type` | VARCHAR | Duplicated for display without join |
| `overall_score` | FLOAT | 0–100 percentage |
| `per_question_scores` | TEXT | JSON array: `[8, 6, 7, 5, 8, 7, 6, 8]` |
| `per_dimension_scores` | TEXT | JSON: `{technical: 7.2, clarity: 8.1}` |
| `top_strengths` | TEXT | JSON array of top 3 |
| `top_weaknesses` | TEXT | JSON array of top 3 |
| `suggestions` | TEXT | JSON array of top 5 |
| `created_at` | DATETIME | Report generation time |

**Implementation note:** JSON is stored as TEXT in SQLite (no native JSON type). In PostgreSQL, these would use the JSONB column type. The application handles serialisation/deserialisation transparently.

---

## 7. LangChain Layer — AI Orchestration

All AI logic is isolated in `backend/app/langchain_layer/`. Nothing outside this directory imports LangChain directly — services call into this layer only. This ensures clean separation and easy swap of LLM providers.

### Directory Structure

```
langchain_layer/
├── chains/
│   ├── question_chain.py    ← Generates next interview question (LCEL)
│   └── evaluation_chain.py  ← Scores user answers (JsonOutputParser)
├── prompts/
│   ├── technical_prompt.py
│   ├── system_design_prompt.py
│   ├── behavioral_prompt.py
│   └── resume_interview_prompt.py
├── retrievers/
│   └── dual_retriever.py    ← Resume chunks + Knowledge chunks merged
├── memory/
│   └── session_memory.py    ← ConversationBufferWindowMemory per session
├── vector_store/
│   └── store_manager.py     ← ChromaDB init + BAAI embeddings
└── llm_factory.py           ← Single LLM builder with fallback strategy
```

### QuestionChain (LCEL)

```
Input: { user_answer, question_number, history }
    │
    ├── DualRetriever → format_docs → "context" string
    │
    ├── ConversationBufferWindowMemory → "history" messages
    │
    └── ChatPromptTemplate (per interview type)
              │
              ▼
         ChatGroq (llama-3.3-70b-versatile, temperature=0.7)
              │
              ▼
         StrOutputParser
              │
              ▼
    "You mentioned Hyperledger Fabric. Can you explain the consensus mechanism you chose?"
```

**Output:** Plain string — the next question to ask.

### EvaluationChain (LCEL + Structured Output)

```
Input: { question, user_answer, context, interview_type }
    │
    └── ChatPromptTemplate with SCORING GUIDE
              │
              ▼
         ChatGroq (temperature=0.2 — deterministic scoring)
              │
              ▼
         JsonOutputParser
              │
              ▼
    {
      "technical_correctness": 7,
      "depth_of_explanation": 6,
      "clarity": 8,
      "overall_score": 7,
      "strengths": ["Correct B-tree explanation", "Good example used"],
      "weaknesses": ["Missed Hash index type"],
      "suggestions": ["Read about Hash indexes", "Practice composite indexes"]
    }
```

**Why JsonOutputParser?**  
`StrOutputParser` returns plain text requiring fragile regex parsing. `JsonOutputParser` instructs the LLM to output valid JSON and parses it automatically — reliable even with long model outputs.

### Evaluation Scoring Guide (Calibrated)

After multiple tuning iterations, the final scoring rubric:

| Score | Meaning |
|-------|---------|
| 0 | Complete non-answer — "I don't know", "CANT", blank |
| 2–3 | Minimal — acknowledged topic but no real explanation |
| 4–5 | Partial — shows familiarity, missing key points |
| 6–7 | Good — correct understanding, could be deeper |
| 8–9 | Strong — thorough, well communicated, minor gaps |
| 10 | Excellent — comprehensive, clear, nothing missing |

**Framing:** "friendly mock interview coach" — balanced, encouraging feedback rather than harsh scores.

### Conversation Memory

```python
# ConversationBufferWindowMemory with k=6 exchanges
# At message N: inject last 6 Q/A pairs into the prompt
history = get_history(session_id)

# After processing:
save_exchange(session_id, user_answer, ai_question)
# Adds to in-memory window
```

**Why WindowMemory(k=6)?** Full memory grows unbounded and would exceed the LLM's context limit for long sessions. A window of 6 exchanges holds all 8 interview questions without overflow.

### LLM Factory with Automatic Fallback

```python
# llm_factory.py
primary = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
fallback = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)
llm = primary.with_fallbacks([fallback])
# If primary returns HTTP 429, LangChain transparently retries with fallback
```

### Prompt Templates (Per Interview Type)

Each interview type has a dedicated prompt file:

| File | Persona | Focus |
|------|---------|-------|
| `technical_prompt.py` | Senior engineer | CS concepts, technology depth |
| `system_design_prompt.py` | Staff engineer | Architecture, scalability |
| `behavioral_prompt.py` | Hiring manager | STAR stories, soft skills |
| `resume_interview_prompt.py` | Recruiter | CV deep-dive, project decisions |

**Common structure:**
```python
ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),      # Persona + rules + {context} + {question_number}
    MessagesPlaceholder("history"),  # LangChain memory injects here
    ("human", HUMAN_TEMPLATE),      # Current task with {user_answer} and {question_number}
])
```

**Critical fix — repeated greeting bug:** The `{question_number}` variable existed in the system prompt but NOT in the human message template. The LLM never saw the number at generation time and re-introduced itself on every question ("Hi, I'm your technical interviewer today" appeared on questions 3, 5, 8). Fix: add `{question_number}` to the human template with explicit rule: *"If question_number ≥ 2: output ONLY the question. No greeting. No self-introduction."*

### Why LangChain's Power Matters — Provider Swap in One Line

```python
# TODAY: Groq Llama
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile")

# TOMORROW: OpenAI GPT — only THIS line changes
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini")

# ALL chains stay IDENTICAL
chain = prompt | llm | output_parser
```

---

## 8. Backend Implementation — FastAPI

### Repository Structure

```
backend/
├── app/
│   ├── main.py                 ← FastAPI app entry + lifespan + CORS
│   ├── config.py               ← Settings via pydantic-settings (env vars)
│   │
│   ├── api/
│   │   ├── error_utils.py      ← Unified api_error() helper (canonical error shape)
│   │   └── routes/
│   │       ├── auth.py         ← Auth status endpoint (stub for future JWT)
│   │       ├── resume.py       ← Resume upload, get, embedding status
│   │       ├── session.py      ← Session CRUD, start, message, end
│   │       └── report.py       ← Report generation and retrieval
│   │
│   ├── services/               ← Business logic (no LangChain imports here)
│   │   ├── resume_service.py   ← PDF parsing, embedding, DB persistence
│   │   ├── session_service.py  ← Interview orchestration loop
│   │   └── report_service.py   ← Evaluation aggregation and report building
│   │
│   ├── langchain_layer/        ← All AI code (see Section 7)
│   │
│   ├── models/                 ← SQLModel DB table definitions
│   │   ├── user.py
│   │   ├── resume.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── evaluation.py
│   │   └── report.py
│   │
│   └── db/
│       └── database.py         ← SQLite engine + session factory
│
├── knowledge_base/             ← Curated markdown docs for RAG ingestion
├── knowledge_raw/              ← Auto-collected HTML/PDF sources (gitignored)
├── scripts/
│   ├── ingest_knowledge.py          ← Embed all docs → ChromaDB
│   ├── collect_knowledge_sources.py ← Auto-download from seed URLs
│   ├── test_phase2_resume.py
│   ├── test_phase3_session.py
│   ├── test_phase4_report.py
│   ├── test_phase5_edge_cases.py
│   └── test_phase5_pdf_relevance.py
│
├── vector_store_data/          ← ChromaDB persisted index (gitignored)
├── Dockerfile                  ← Multi-stage: pre-downloads BAAI model
└── requirements.txt
```

### API Endpoints

#### Resume API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/resume/upload?guest_id=UUID` | Upload PDF → parse with LLM → embed in ChromaDB |
| `GET` | `/api/resume/{id}` | Get parsed resume by ID |
| `GET` | `/api/resume/guest/{guest_id}` | Get latest resume by guest UUID |
| `GET` | `/api/resume/{id}/status` | Check embedding progress (`chunks_embedded`) |

#### Session API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/session/` | Create a new session row (fast, synchronous) |
| `GET` | `/api/session/{id}/start` | Generate opening question (async LLM call) |
| `GET` | `/api/session/{id}` | Get session state + all message history |
| `POST` | `/api/session/{id}/message` | Core loop: submit answer → get evaluation + next Q |
| `POST` | `/api/session/{id}/end` | Early termination, triggers report generation |

#### Report API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/report/{session_id}` | Get or generate report (idempotent) |
| `GET` | `/api/report/{session_id}?regenerate=true` | Force recalculation |

### Unified Error Response Shape

All error responses across the entire API follow one canonical structure:

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

This is enforced via `error_utils.py::api_error()` called consistently in every route.

### Resume Upload Pipeline (Step-by-Step)

```
PDF bytes
    │
    ▼ Step 1: PyMuPDF (fitz)
    raw text string
    │
    ▼ Step 2: LangChain Chain → Groq LLM → JsonOutputParser
    { name, skills, projects, experience, education }
    │
    ├──▶ Step 3: SQLite DB → Resume row (raw_text + parsed_json + chunks_embedded=False)
    │
    └──▶ Step 4 (BackgroundTask): ChromaDB
         - Delete old chunks for this guest_id (stale chunk cleanup)
         - Build structured semantic chunks
         - Embed with BAAI model → ChromaDB resume_store
         - Update chunks_embedded=True
```

### Report Service — Aggregation Logic

1. Validate session is completed
2. Fetch all `Evaluation` rows ordered by `question_number`
3. Compute `per_question_scores` array
4. Compute per-dimension averages: `technical_correctness`, `depth_of_explanation`, `clarity`, `overall`
5. Compute headline `overall_score = average(overall_0_to_10) * 10` (0–100 scale)
6. Parse all strengths/weaknesses/suggestions JSON arrays
7. Count phrase frequency with `Counter`
8. Store: top 3 strengths, top 3 weaknesses, top 5 suggestions
9. Persist as `Report` row (idempotent — one report per session)

**Report response example:**
```json
{
  "report_id": 1,
  "session_id": 5,
  "interview_type": "technical",
  "overall_score": 75.0,
  "per_question_scores": [7, 8, 6, 9],
  "per_dimension_scores": {
    "technical_correctness": 7.5,
    "depth_of_explanation": 7.5,
    "clarity": 7.75,
    "overall": 7.5
  },
  "top_strengths": ["Clear explanation of B-tree", "Good example used"],
  "top_weaknesses": ["Could add more detail on Hash indexes"],
  "suggestions": ["Practice composite index scenarios", "Read about Hash indexes"]
}
```

### Environment Configuration

```bash
# Required
GROQ_API_KEY=gsk_YOUR_KEY_HERE        # console.groq.com/keys (free)

# Model selection
GROQ_MODEL=llama-3.3-70b-versatile     # Primary model (production quality)
GROQ_FALLBACK_MODEL=llama-3.1-8b-instant  # Fallback on HTTP 429
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5  # DO NOT change after ingestion

# Database
DATABASE_URL=sqlite:////app/data/preplingo.db

# Storage
VECTOR_STORE_PATH=./vector_store_data

# App
APP_ENV=production
```

---

## 9. Frontend Implementation — Streamlit

### Design Decision: Streamlit over Next.js

The original architecture planned for a Next.js 14 (App Router) frontend. After MVP assessment, Streamlit was chosen for the following reasons:

- No separate build pipeline (no npm, TypeScript, webpack, or bundler)
- Full Python stack — same language as the backend
- Rapid iteration on layout and state without component boilerplate
- Native support for file upload, metrics, charts, and progress bars
- Custom CSS injected via `st.markdown(unsafe_allow_html=True)`
- Calls FastAPI backend directly via Python `requests`

The Next.js architecture remains documented as the target for a future production-grade frontend.

### App Architecture

```
frontend_streamlit/
├── app.py                    ← Single-file Streamlit application (~600 lines)
└── .streamlit/
    └── config.toml           ← Light theme base + server config
```

### Session State Keys

| Key | Type | Purpose |
|-----|------|---------|
| `guest_id` | str (UUID4) | Unique guest identifier, persists across reruns |
| `resume_id` | int | DB ID of the uploaded resume |
| `resume_data` | dict | Parsed CV data (skills, projects) from upload response |
| `session_id` | int | Active interview session ID |
| `interview_type` | str | `technical / system_design / behavioral / resume` |
| `messages` | list[dict] | Full conversation history with evaluations |
| `started` | bool | Whether the interview session has started |
| `session_complete` | bool | Whether all 8 questions have been answered |
| `last_report` | dict | Final report payload |
| `resume_chunks_embedded` | bool | Whether background CV embedding completed |

### Rendering Flow

```
main()
  ├── set_page_config()
  ├── ensure_state()
  ├── inject_styles()          ← Custom CSS (Google Fonts, colors, cards)
  ├── render_header()          ← Logo + "New Interview" reset button
  │
  ├── columns([left, right])
  │   ├── resume_step()        ← Step 1: Upload CV, display skills/projects
  │   └── setup_session_step() ← Step 2: Pick interview type, create session
  │
  ├── interview_step()         ← Step 3: Q/A timeline + score pills + chat input
  └── report_step()            ← Step 4: Final report with chart and feedback grid
```

### User Flow (Happy Path)

1. Open app → `ensure_state()` generates a `guest_id`
2. Upload PDF → `POST /api/resume/upload` → receive `resume_id` + parsed skills/projects
3. Background embedding starts automatically (FastAPI `BackgroundTasks`)
4. User sees "Embedding in background..." + manual Refresh button
5. Select interview type → click "Create Session" → `POST /api/session/`
6. App calls `GET /api/session/{id}/start` → receives first AI question
7. User types answer → `POST /api/session/{id}/message`
8. App shows evaluation scores inline (colour-coded score pills + feedback box)
9. Repeat for 8 questions → `session_complete = True`
10. Click "Fetch Report" → `GET /api/report/{id}` → full report rendered

### Visual Design System

| Role | Colour | Usage |
|------|--------|-------|
| Background | `#f6f4ee` (warm ivory) | App base |
| Panel | `#fffdf8` (cream white) | Step cards |
| Accent teal | `#0f766e` | Questions, active accents |
| Accent indigo | `#6366F1` | Buttons, wizard active state |
| Score-high (≥7) | `#d1fae5` / `#0d7d56` | Green pills |
| Score-mid (4–6) | `#fef3c7` / `#92400e` | Amber pills |
| Score-low (<4) | `#fee2e2` / `#dc2626` | Red pills |

**Typography:** Fraunces (serif headings) + Space Grotesk (body) via Google Fonts

### Resilience Features

- **Upload timeout recovery:** If upload times out, app auto-calls `GET /api/resume/guest/{guest_id}` to recover the already-processed resume
- **API error handling:** All errors shown inline with `st.error()` — no page crash
- **Re-upload deduplication:** Old ChromaDB chunks are deleted before new ones are inserted
- **New Interview reset:** "↺ New Interview" button resets all state but preserves `guest_id`

---

## 10. Knowledge Base and Ingestion Pipeline

### Supported Source Formats

The ingestion pipeline accepts: `.md`, `.txt`, `.pdf`, `.docx`, `.html`/`.htm`

### Two Source Roots

1. `backend/knowledge_base/` — curated markdown documents (version-controlled)
2. `backend/knowledge_raw/` — external articles auto-downloaded from seed URLs (gitignored)

### Automated Source Collection

`backend/scripts/collect_knowledge_sources.py` reads seed URLs from `backend/knowledge_raw/seed_sources.json`, discovers topic-relevant links, and downloads HTML/PDF files into topic folders.

### Ingestion Behavior

1. Scan all supported files in both roots
2. Skip noise files (`README`, `collector_README`, `seed_sources`, `discovery_report`, `index`)
3. Parse and normalise text based on file type
4. Chunk using `RecursiveCharacterTextSplitter`
5. Apply content-hash deduplication — skip identical documents
6. Replace chunks by `source` in ChromaDB (no duplicates on re-run)
7. Embed and store in `knowledge` collection
8. Run a retrieval smoke test to verify

**Reset mode:**
```bash
python scripts/ingest_knowledge.py --reset
# Deletes and rebuilds only the knowledge collection
```

### Metadata Schema

```python
{
  "source": "technical/databases.md",
  "source_type": "markdown",
  "interview_type": "technical",
  "topic": "databases",
  "title": "Database Indexing",
  "content_hash": "sha256:...",
  "chunk_index": 0,
  "chunk_hash": "sha256:..."
}
```

---

## 11. Implementation Phases and Timeline

### Phase 0/1 — Foundation (2026-03-12)

**What was built:**
- All 17 spec documents drafted (architecture, RAG design, data models, chains, all phases)
- FastAPI app skeleton (`main.py`, `config.py`, CORS, routers)
- SQLModel data models (6 tables)
- LangChain layer scaffolded (chains, prompts, retrievers, memory, vector store)
- Initial knowledge base markdown content created
- Test script structure defined

**Duration:** ~6 hours (specs started 12:00 PM, code at 1:29 PM)

### Phase 2 — Resume Pipeline (2026-03-12–13)

**What was built:**
- `resume_service.py` — PDF extraction + LLM parsing + ChromaDB embedding
- Full resume API routes (`/upload`, `/get`, `/guest/{id}`)
- ChromaDB collections initialised
- `test_phase2_resume.py` — 6 automated integration tests

**Test results:**
```
✅ Health check
✅ PDF upload + Gemini parse + ChromaDB embed (3 chunks stored)
✅ GET /api/resume/{id} — all fields returned
✅ GET /api/resume/guest/{guest_id} — resume found
✅ Non-PDF rejected with 400 Bad Request
✅ ChromaDB retrieval — resume chunks searchable
```

**LLM switch:** Gemini daily RPD quota exhausted → switched to Groq (Llama 3.3 70B) for all inference.

### Phase 3 — Session Service & AI Loop (2026-03-13)

**What was built:**
- `session_service.py` — the core interview orchestration engine
- Full session API routes (create, start, message, get, end)
- `QuestionChain` and `EvaluationChain` with Groq LLM
- `ConversationBufferWindowMemory` per session
- `DualRetriever` (resume + knowledge)
- `test_phase3_session.py` — 7 automated integration tests

**Test results:**
```
✅ Health check
✅ Create session (type=technical)
✅ Get first question (GET /start)
✅ Send answer → Evaluated 4/10 + next question generated
✅ Send answer → Evaluated again + next question generated
✅ Get session history (5 messages in DB verified)
✅ Validation — can't call /start twice (double-start blocked)
✅ End session
```

**Example AI output captured:**
> "You've had experience with indexing in PostgreSQL. Can you explain the difference between a clustered index and a non-clustered index, and provide a scenario where you would choose to use each?"

### Phase 4 — Report Service (2026-03-13–16)

**What was built:**
- `report_service.py` — evaluation aggregation and report persistence
- Full report API (`/report/{session_id}` with idempotency and `?regenerate=true`)
- Session integration (auto-generate report on natural completion)
- `test_phase4_report.py` — 6 automated integration tests

**Test results:**
```
✅ Health check
✅ Create session
✅ Seed evaluations + mark session completed
✅ GET /api/report/{id} generates report
✅ Second GET is idempotent (same report_id returned)
✅ Add evaluation + ?regenerate=true recomputes correctly
```

**Observed runtime values:**
- Initial: `overall_score = 70.0`, `per_question_scores = [7, 8, 6]`
- After regeneration with stronger answer: `overall_score = 75.0`, `per_question_scores = [7, 8, 6, 9]`

### Phase 5 — Guest MVP Hardening (2026-03-16–17)

**What was built:**

1. **Embedding model migration:** Gemini → BAAI/bge-base-en-v1.5 (local, no API calls, higher MTEB score)
2. **Structured CV chunks:** Semantic chunking from LLM-parsed JSON instead of raw text splitting
3. **Stale chunk deletion:** Delete old ChromaDB chunks before re-upload
4. **Evaluation prompt tuning:** Fixed all-zero scores bug and inflated scores for non-answers
5. **Repeated greeting fix:** Added `{question_number}` to human template in all 4 prompt files
6. **Knowledge ingestion hardening:** Filename filters + content-hash deduplication
7. **Frontend process button fix:** Removed blocking polling loop, added manual refresh
8. **Full Streamlit frontend:** Complete professional UI with all 4 interview types
9. **Docker Compose setup:** Multi-stage Dockerfile with BAAI model baked in
10. **Edge case test suite:** `test_phase5_edge_cases.py` + `test_phase5_pdf_relevance.py`

**Edge case test results:**
```
✅ Missing resume_id for resume-mode blocked (400)
✅ Resume ownership mismatch blocked (403)
✅ Message before /start blocked (400)
✅ Report before completion blocked (400)
✅ Latest resume-by-guest returns newest record
```

**PDF relevance test results:**
```
✅ PDF upload succeeded and resume parsed
✅ Resume session created with uploaded resume_id
✅ First AI question referenced uploaded project context (PrepLingo)
✅ Resume-mode validation without resume_id blocked (400)
```

### Phase Deployment — GCP (2026-03-18)

**What was built:**

1. **LLM upgrade:** Primary model upgraded to `llama-3.3-70b-versatile`; fallback mechanism via `with_fallbacks()`
2. **Frontend containerisation:** `frontend_streamlit/Dockerfile` + `BACKEND_URL` env var
3. **Full Docker Compose:** Three services (backend, frontend, nginx) with named volumes
4. **Docker build debugging:** Resolved 6 build/runtime issues (see Section 14)
5. **GCP VM provisioned:** e2-medium, Ubuntu 22.04, 30 GB SSD
6. **Application deployed live:** All containers running and healthy

---

## 12. Production Deployment — GCP

### Infrastructure Stack

| Component | Specification |
|-----------|--------------|
| Cloud | Google Cloud Platform (GCP) |
| VM | Compute Engine e2-medium (2 vCPU, 4 GB RAM, 30 GB SSD) |
| OS | Ubuntu 22.04 LTS |
| Container runtime | Docker + Docker Compose v2 |
| Reverse proxy | Nginx 1.25 |
| Backend | FastAPI + Uvicorn (internal port 8000) |
| Frontend | Streamlit (internal port 8501) |
| Public access | Port 80 (HTTP), configurable for 443 (HTTPS + Let's Encrypt / Cloudflare) |

### Docker Compose Service Architecture

**backend:**
- Multi-stage Dockerfile
- Stage 1 (builder): installs CPU-only PyTorch, all Python deps, downloads BAAI model
- Stage 2 (runtime): copies built site-packages, bins, and model → slim final image
- Named volumes: `embedding-cache` (HuggingFace model), `vector-data` (ChromaDB), `db-data` (SQLite at `/app/data/preplingo.db`)
- Health check: `GET /health` every 30s

**frontend:**
- Simple Python image
- `BACKEND_URL=http://backend:8000` (internal Docker network)
- Starts only after backend health check passes

**nginx:**
- Routes `/api/*` → `backend:8000`
- Routes `/*` → `frontend:8501`
- WebSocket upgrade headers for Streamlit's live connection
- DNS resolver: `127.0.0.11` (Docker's internal DNS) with `set $var` variable upstream to prevent startup failure before containers are ready

### Deployment Quick Reference

```bash
# First deployment
git clone https://github.com/YOUR_USERNAME/PrepLingo.git ~/PrepLingo
cd ~/PrepLingo
cp .env.example .env && nano .env    # Set GROQ_API_KEY
docker compose up --build -d
docker compose exec backend python scripts/ingest_knowledge.py

# Update deployment
git pull
docker compose up --build -d

# Verify
curl http://YOUR_VM_IP/health        # → {"status": "ok"}
```

### Domain and HTTPS (Optional)

For a custom subdomain like `preplingo.yourname.me`:

1. Purchase `.me` domain at Porkbun or Namecheap (~$5–15/year)
2. Move DNS to Cloudflare (free tier)
3. Add A record: `preplingo → VM_IP` with proxy ON (Cloudflare handles HTTPS)
4. Update `nginx.conf`: `server_name preplingo.yourname.me;`
5. Cloudflare Flexible SSL provides HTTPS at zero server-side configuration

---

## 13. Testing and Quality Assurance

### Automated Test Suites

| Script | Phase | Tests |
|--------|-------|-------|
| `test_phase2_resume.py` | Resume Pipeline | 6 tests: upload, parse, embed, get, reject non-PDF, ChromaDB retrieval |
| `test_phase3_session.py` | Session & AI Loop | 7 tests: create, start, message (2 turns), history, double-start block, end |
| `test_phase4_report.py` | Report Service | 6 tests: generate, idempotency, regenerate after new evaluation |
| `test_phase5_edge_cases.py` | Hardening | 5 tests: ownership, missing resume_id, message-before-start, report-before-completion, latest-resume |
| `test_phase5_pdf_relevance.py` | RAG Grounding | 4 tests: upload, session creation, first question relevance check, validation |

**Total: 28 automated integration tests covering the full system.**

### Manual QA Checklist

**Positive flows:**
- Upload PDF → parse → embed → confirm parsed fields
- Create session (all 4 interview types)
- Start session → confirm first question is CV-aware
- Send answers → confirm score increments and evaluation shape
- End session → fetch report → confirm valid report structure

**Negative flows (deterministic error shape verified):**
- Resume upload with non-PDF → 400
- Session creation with interview_type=resume and no resume_id → 400
- Resume ownership mismatch → 403
- Message before /start → 400
- Report before session completion → 400

### Key Bug Fixes Discovered Through Testing

1. **All-zero evaluation scores** — Over-aggressive non-answer detection fired on real answers
2. **Inflated scores for "cant"** — Literal non-answers receiving 5/10 with fabricated strengths
3. **Repeated greetings** — `{question_number}` missing from human message template
4. **Upload timeout leaving broken state** — Added auto-recovery via guest resume lookup
5. **Process Resume button unresponsive** — Blocking `time.sleep()` polling loop froze Streamlit event loop
6. **Re-upload duplication** — Old ChromaDB chunks not deleted before new ingestion
7. **Knowledge ingestion noise** — README and seed files being embedded into ChromaDB

---

## 14. Key Engineering Challenges and Solutions

### Challenge 1: Gemini Quota Exhaustion

**Problem:** After heavy testing during Phase 2, the Gemini free tier daily RPD quota was exhausted (`404 GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit: 0`).

**Solution:** Switched all LLM inference to Groq with `llama-3.3-70b-versatile` as primary and `llama-3.1-8b-instant` as automatic fallback via LangChain's `with_fallbacks()` API. Groq's free tier offers 14,400 requests/day on LPU hardware — near-instant generation, no quota issues.

### Challenge 2: Embedding API Contention (25-Second Timeout)

**Problem:** After the first answer, question generation timed out at 25 seconds. Root cause: background CV embedding and the DualRetriever query embedding both called the Google Embedding API simultaneously, causing contention.

**Solution:** Migrated to `BAAI/bge-base-en-v1.5` (local HuggingFace model). Runs entirely locally, zero API calls, zero contention. MTEB score 72.3 vs Gemini's ~71.0 — actually higher quality. Pre-downloaded into the Docker image at build time to eliminate cold-start.

### Challenge 3: Docker Image Size (Disk Full on GCP VM)

**Problem:** `sentence-transformers` triggers installation of the full CUDA-enabled PyTorch build (~2.5 GB of nvidia-* libraries) even on a CPU-only server. This filled the 30 GB GCP VM disk during build.

**Solution:** Pre-install CPU-only PyTorch before the main `requirements.txt` install:
```dockerfile
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt
```
This reduced the image size by ~2.3 GB.

### Challenge 4: SQLite Database Not Found in Container

**Problem:** The `db-data:/app` volume mount shadowed the entire `/app` directory, hiding application code on container restarts and preventing SQLite from writing.

**Solution:** Changed the mount path to `/app/data` and updated `DATABASE_URL=sqlite:////app/data/preplingo.db`. Application code at `/app/` is unchanged; database lives at `/app/data/` on its own volume.

### Challenge 5: Nginx DNS Resolution at Startup

**Problem:** Nginx resolves upstream hostnames at startup, before backend/frontend containers are ready. This caused "host not found in upstream" errors.

**Solution:** Added Docker's internal DNS resolver and dynamic variable upstreams:
```nginx
resolver 127.0.0.11 valid=10s;
set $backend backend:8000;
proxy_pass http://$backend;
```
Resolution now happens at request time rather than at Nginx startup.

### Challenge 6: GCP Firewall Blocking Port 80

**Problem:** The application was running correctly inside the VM but all HTTP traffic was rejected by GCP's default network firewall.

**Solution:** Created an `allow-http` firewall rule in VPC Network → Firewall permitting TCP port 80 from all sources (`0.0.0.0/0`).

### Challenge 7: Knowledge Base Noise in ChromaDB

**Problem:** Admin files (README, collector_README, discovery_report) and seed files were being ingested into ChromaDB, polluting knowledge retrieval results.

**Solution:** Added `_SKIP_STEMS` frozenset and `_SKIP_PREFIXES` tuple to `ingest_knowledge.py`, plus content-hash deduplication so identical content from different seed copies is skipped automatically.

### Challenge 8: Streamlit Process Button Unresponsive

**Problem:** The "Process Resume" button stopped responding after one click. A `time.sleep()` polling loop was blocking the Streamlit event loop.

**Solution:** Removed the blocking polling loop entirely. Replaced with a lightweight manual "Refresh" button that calls `GET /api/resume/{id}/status`. Added timeout-recovery logic: if upload times out, auto-calls `GET /api/resume/guest/{guest_id}` to recover the already-processed resume.

---

## 15. Future Roadmap — Voice Upgrade

A full voice interview plan was designed as the next major enhancement (SPEC 17).

### Core Insight

The voice feature is purely an I/O layer change — the entire LangChain pipeline, Groq LLM, ChromaDB retrieval, and evaluation logic require **zero changes**.

```
User speaks into mic (browser)
        ↓ [STT: speech → text]
Transcribed text (string)
        ↓ POST /api/session/{id}/message  ← same existing endpoint
session_service.process_message()  ← completely unchanged
        ↓ { ai_question: "text..." }
        ↓ [TTS: text → audio]
Audio plays back to user
```

### Recommended Implementation (Phase 1 — Option B)

**New backend endpoints:**
- `POST /api/voice/transcribe` — accepts audio, returns `{ text: "..." }` via Whisper API
- `POST /api/voice/synthesize` — accepts text, returns audio via OpenAI TTS / ElevenLabs
- `POST /api/session/{id}/voice-message` — combined: audio in → transcribe → process → synthesize → audio out

**Estimated cost per 15-minute interview (~10 questions):**
- STT (OpenAI Whisper): ~$0.09
- TTS (OpenAI TTS or ElevenLabs): ~$0.075
- **Total: ~$0.17 per interview** (on top of existing free Groq tier)

**Phase 2 option:** Pipecat framework with streaming Deepgram STT + ElevenLabs TTS via Daily.co WebRTC transport for sub-second latency. Similar cost (~$0.15/interview), much better conversational feel.

---

## 16. Key Decisions and Rationale

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | LLM Provider | **Groq (Llama 3.3 70B)** | LPU hardware = ~2-4s generation, free tier, 14,400 req/day |
| 2 | LLM Fallback | **Llama 3.1 8B Instant** | Automatic via `with_fallbacks()` on HTTP 429 |
| 3 | Embeddings | **BAAI/bge-base-en-v1.5 (local)** | MTEB 72.3 > Gemini 71.0, no API dependency, no rate limits |
| 4 | Vector Store | **ChromaDB** | Persistent, metadata filtering, LangChain native integration |
| 5 | CV in RAG | **Structured semantic chunks** | One chunk per project = precise retrieval vs raw text splitting |
| 6 | Evaluation timing | **Per answer (real-time)** | Immediate feedback improves interview simulation realism |
| 7 | Session length | **Fixed 8 questions** | Predictable UX, sufficient for meaningful performance report |
| 8 | Auth strategy | **Guest mode (deferred JWT)** | Ships faster, enables real user trials without registration friction |
| 9 | AI framework | **Full LangChain LCEL** | Modern standard, provider-agnostic, full educational value |
| 10 | Report strategy | **Persisted + idempotent** | Cached by default, forced regeneration supported |
| 11 | Frontend | **Streamlit** | Python-native, no build pipeline, full-featured for MVP |
| 12 | Embedding deployment | **Pre-downloaded in Docker image** | Zero cold-start download; model baked into image layer |
| 13 | Error responses | **Unified canonical shape** | One `api_error()` helper used everywhere |

---

## 17. Learning Outcomes

Building PrepLingo end-to-end provided hands-on experience with the following:

### AI/ML Engineering
- **LangChain LCEL chain composition** — building multi-step pipelines with `|` operator, `RunnablePassthrough`, `RunnableParallel`
- **RAG pipeline design** — two-phase ingestion (knowledge base + per-user resume), dual retrieval, context injection
- **Vector database management** — ChromaDB collection design, metadata filtering, chunk strategy, deduplication
- **Prompt engineering** — multi-turn conversation prompts, structured output instructions, scoring guides, persona framing
- **Structured LLM output** — `JsonOutputParser` for reliable evaluation scoring without regex parsing
- **Embedding model selection** — MTEB benchmark, vector dimensions, local vs API trade-offs
- **LLM provider strategy** — fallback chains, rate limit handling, provider-agnostic architecture

### Backend Engineering
- **FastAPI** — async route handlers, background tasks, middleware, lifespan events, auto OpenAPI docs
- **SQLModel** — combining Pydantic validation with SQLAlchemy ORM, table definitions, relationships
- **SQLite for production** — volume-persisted Docker deployment, absolute path configuration
- **REST API design** — idempotent endpoints, canonical error shapes, guest-mode auth pattern

### DevOps and Infrastructure
- **Docker multi-stage builds** — builder stage installs deps + downloads ML models; slim runtime stage copies artifacts
- **Docker Compose v2** — multi-service orchestration, named volumes, health checks, depends_on
- **Nginx reverse proxy** — upstream routing, WebSocket upgrade headers, Docker DNS resolver
- **GCP Compute Engine** — VM provisioning, firewall rules, SSH access, Docker installation
- **CPU-only PyTorch** — index-URL pip install to avoid CUDA dependencies on server
- **Domain and DNS** — Cloudflare DNS management, A records, SSL via Cloudflare proxy

### Software Architecture
- **Layer separation** — services call langchain_layer, routes call services, never crossing concerns
- **Configuration management** — all environment variables via `pydantic-settings`, no hardcoded values
- **Test-driven debugging** — per-phase integration test suites as the primary debugging tool
- **Spec-driven development** — 17 specification documents written before and alongside implementation

---

## Appendix A — Project File Inventory

```
PrepLingo/
├── specs/                          (17 specification documents + DECISIONS.md)
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── error_utils.py
│   │   │   └── routes/ (auth.py, resume.py, session.py, report.py)
│   │   ├── services/ (resume_service.py, session_service.py, report_service.py)
│   │   ├── langchain_layer/
│   │   │   ├── chains/ (question_chain.py, evaluation_chain.py)
│   │   │   ├── prompts/ (4 prompt files)
│   │   │   ├── retrievers/ (dual_retriever.py)
│   │   │   ├── memory/ (session_memory.py)
│   │   │   ├── vector_store/ (store_manager.py)
│   │   │   └── llm_factory.py
│   │   ├── models/ (6 model files)
│   │   └── db/ (database.py)
│   ├── knowledge_base/ (curated markdown docs per interview type)
│   ├── knowledge_raw/ (auto-collected sources + seed config)
│   ├── scripts/ (ingest_knowledge.py, collect_knowledge_sources.py, 5 test scripts)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend_streamlit/
│   ├── app.py
│   ├── Dockerfile
│   └── .streamlit/config.toml
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
└── README.md
```

**Total: 47 source files, 227 code nodes, 1,997 code relationships (per knowledge graph analysis)**

---

## Appendix B — API Reference Summary

### Base URL

- Local: `http://localhost:8000`
- Production: `http://YOUR_VM_IP` (or custom domain)

### Endpoints

```
GET  /health                                    → Health check
GET  /docs                                      → Swagger UI

POST /api/resume/upload?guest_id=UUID           → Upload PDF resume
GET  /api/resume/{id}                           → Get resume by ID
GET  /api/resume/guest/{guest_id}               → Get latest resume by guest
GET  /api/resume/{id}/status                    → Check embedding status

POST /api/session/                              → Create interview session
GET  /api/session/{id}/start                    → Generate first AI question
GET  /api/session/{id}                          → Get session + message history
POST /api/session/{id}/message                  → Submit answer, get next Q + evaluation
POST /api/session/{id}/end                      → End session early

GET  /api/report/{session_id}                   → Get or generate report
GET  /api/report/{session_id}?regenerate=true   → Force report recalculation
```

---

*Document generated from project source code, specification documents, and git history.*  
*PrepLingo v0.1 — AI Interview Trainer — March 2026*
