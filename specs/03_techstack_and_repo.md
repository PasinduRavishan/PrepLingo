# SPEC 03 — Tech Stack & Repository Structure

**Status:** Draft — Pending Decisions

---

## Tech Stack (Proposed)

### Backend
| Layer | Technology | Why |
|---|---|---|
| Web Framework | **FastAPI** (Python 3.11+) | Async-native, auto OpenAPI docs, Pydantic-first |
| AI Orchestration | **LangChain** (LCEL) | Chains, retrievers, memory, prompt templates |
| LLM Provider | **TBD** (see Decisions) | — |
| Embeddings | **TBD** (see Decisions) | — |
| Vector Store | **TBD** (see Decisions) | — |
| PDF Parsing | **PyMuPDF** (fitz) | Fast, reliable, Python-native |
| ORM | **SQLModel** | Built for FastAPI, Pydantic models = DB models |
| Database | **SQLite** (dev) → PostgreSQL (prod) | Zero setup for dev |
| Auth | **python-jose** + **passlib** (bcrypt) | JWT implementation |
| Server | **Uvicorn** | ASGI server for FastAPI |
| Package Mgr | **pip** + **requirements.txt** or **Poetry** | TBD |

### Frontend
| Layer | Technology | Why |
|---|---|---|
| Framework | **Next.js 14** (App Router) | File-based routing, SSR, React ecosystem |
| Language | **TypeScript** | Type safety, better DX |
| Styling | **Tailwind CSS** | Rapid UI, utility-first |
| State Management | **Zustand** | Simple, lightweight, no boilerplate |
| HTTP Client | **Axios** | Auto JSON, interceptors for auth |
| UI Components | **shadcn/ui** | Pre-built accessible components |
| Chat UI | Custom component | Real interview feel |
| Charts (Reports) | **Recharts** | Score visualization (radar chart) |

### Infrastructure (Local Dev)
| Component | Tool |
|---|---|
| Version Control | Git + GitHub |
| Env Vars | `.env` files (python-dotenv / Next.js .env.local) |
| API Docs | FastAPI auto-generates Swagger at `/docs` |
| Knowledge Base Ingestion | Python script (`scripts/ingest_knowledge.py`) |

---

## Repository Structure

```
PrepLingo/
│
├── specs/                          ← All spec documents (this folder)
│   ├── 00_project_overview.md
│   ├── 01_architecture.md
│   ├── 02_rag_design.md
│   ├── 03_techstack_and_repo.md
│   ├── 04_data_models.md
│   ├── 05_api_contracts.md
│   ├── 06_langchain_chains.md
│   └── 07_frontend_pages.md
│
├── backend/                        ← FastAPI + LangChain
│   │
│   ├── app/
│   │   ├── main.py                 ← FastAPI app entry point
│   │   ├── config.py               ← Settings (env vars, LLM config)
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py         ← /auth/register, /auth/login
│   │   │       ├── resume.py       ← /resume/upload, /resume/parse
│   │   │       ├── session.py      ← /session (CRUD + chat)
│   │   │       └── report.py       ← /report/{session_id}
│   │   │
│   │   ├── services/               ← Business logic (no LangChain here)
│   │   │   ├── auth_service.py
│   │   │   ├── resume_service.py
│   │   │   ├── session_service.py
│   │   │   ├── eval_service.py
│   │   │   └── report_service.py
│   │   │
│   │   ├── langchain_layer/        ← ALL LangChain/AI code lives here
│   │   │   │
│   │   │   ├── chains/
│   │   │   │   ├── question_chain.py    ← Generates next interview question
│   │   │   │   └── evaluation_chain.py  ← Scores user's answer
│   │   │   │
│   │   │   ├── prompts/            ← Prompt templates per interview type
│   │   │   │   ├── base_prompt.py
│   │   │   │   ├── resume_interview_prompt.py
│   │   │   │   ├── technical_prompt.py
│   │   │   │   ├── system_design_prompt.py
│   │   │   │   └── behavioral_prompt.py
│   │   │   │
│   │   │   ├── retrievers/
│   │   │   │   └── dual_retriever.py    ← Resume + Knowledge dual retrieval
│   │   │   │
│   │   │   ├── memory/
│   │   │   │   └── session_memory.py    ← Conversation buffer per session
│   │   │   │
│   │   │   └── vector_store/
│   │   │       ├── store_manager.py     ← Init/load vector store
│   │   │       └── ingestion.py         ← Chunk + embed + store
│   │   │
│   │   ├── models/                 ← SQLModel DB models
│   │   │   ├── user.py
│   │   │   ├── session.py
│   │   │   ├── message.py
│   │   │   ├── evaluation.py
│   │   │   └── report.py
│   │   │
│   │   └── db/
│   │       └── database.py         ← SQLite connection + engine
│   │
│   ├── knowledge_base/             ← Raw documents for RAG ingestion
│   │   ├── technical/
│   │   │   ├── databases.md
│   │   │   ├── backend_concepts.md
│   │   │   ├── data_structures.md
│   │   │   ├── networking.md
│   │   │   └── language_specific/
│   │   │       ├── python.md
│   │   │       ├── javascript.md
│   │   │       └── java.md
│   │   │
│   │   ├── system_design/
│   │   │   ├── patterns/
│   │   │   │   ├── caching.md
│   │   │   │   ├── load_balancing.md
│   │   │   │   └── api_design.md
│   │   │   └── case_studies/
│   │   │       ├── url_shortener.md
│   │   │       ├── messaging_system.md
│   │   │       └── social_feed.md
│   │   │
│   │   ├── behavioral/
│   │   │   ├── star_method.md
│   │   │   ├── common_questions.md
│   │   │   └── leadership_principles.md
│   │   │
│   │   └── resume_interview/
│   │       ├── project_questions.md
│   │       └── techstack_deepdive.md
│   │
│   ├── scripts/
│   │   └── ingest_knowledge.py     ← Run once: embed all docs → vector store
│   │
│   ├── vector_store_data/          ← FAISS/ChromaDB persisted index (gitignored)
│   │
│   ├── .env                        ← API keys, DB URL (gitignored)
│   ├── .env.example                ← Template for env vars (committed)
│   └── requirements.txt
│
├── frontend/                       ← Next.js App
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            ← Landing page
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx        ← Upload resume, pick interview type
│   │   │   ├── interview/
│   │   │   │   └── [sessionId]/
│   │   │   │       └── page.tsx    ← Live interview chat
│   │   │   └── report/
│   │   │       └── [sessionId]/
│   │   │           └── page.tsx    ← Final score + feedback
│   │   │
│   │   ├── components/
│   │   │   ├── ChatMessage.tsx     ← Single chat bubble
│   │   │   ├── ChatInterface.tsx   ← Full interview chat area
│   │   │   ├── ResumeUploader.tsx  ← File drag-and-drop upload
│   │   │   ├── InterviewTypeCard.tsx ← Mode selection card
│   │   │   └── ScoreRadarChart.tsx ← Report score visualization
│   │   │
│   │   ├── store/
│   │   │   ├── useSessionStore.ts  ← Zustand: session state
│   │   │   └── useAuthStore.ts     ← Zustand: auth/user state
│   │   │
│   │   └── services/
│   │       └── api.ts              ← Axios client + all API calls
│   │
│   ├── .env.local                  ← NEXT_PUBLIC_API_URL (gitignored)
│   └── package.json
│
├── .gitignore
└── README.md
```

---

## Key Design Rules

1. **LangChain code stays inside `langchain_layer/`** — services call langchain_layer, never import LangChain directly elsewhere
2. **One chain per responsibility** — `QuestionChain` and `EvaluationChain` are separate
3. **Prompts are versioned files** — no inline prompt strings anywhere
4. **Knowledge base docs are human-readable** — `.md` files you can edit and understand
5. **Vector store data is gitignored** — always regenerated from the source `.md` files

---

## Environment Variables (.env.example)

```bash
# LLM
OPENAI_API_KEY=sk-...          # Or GOOGLE_API_KEY for Gemini

# Database
DATABASE_URL=sqlite:///./preplingo.db

# Auth
JWT_SECRET_KEY=your_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Vector Store
VECTOR_STORE_PATH=./vector_store_data
EMBEDDING_MODEL=text-embedding-3-small   # Or local model name

# App
APP_ENV=development
```
