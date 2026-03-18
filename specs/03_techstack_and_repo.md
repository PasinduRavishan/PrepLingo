# SPEC 03 — Tech Stack & Repository Structure

**Status:** Updated — Reflects Phase 5 implementation (2026-03-17)

---

## Tech Stack (Current Implementation)

### Backend
| Layer | Technology | Notes |
|---|---|---|
| Web Framework | **FastAPI** (Python 3.11+) | Async-native, auto OpenAPI docs, Pydantic-first |
| AI Orchestration | **LangChain** (LCEL) | Chains, retrievers, memory, prompt templates |
| LLM Provider | **Groq** (`llama-3.1-8b-instant`) | Fast inference, free tier, no quota issues |
| Embeddings | **BAAI/bge-base-en-v1.5** (local HuggingFace) | 768 dims, MTEB 72.3, no API key, no rate limits |
| Vector Store | **ChromaDB** | Persistent, metadata filtering, LangChain native |
| PDF Parsing | **PyMuPDF** (fitz) | Fast, reliable, Python-native |
| ORM | **SQLModel** | Built for FastAPI, Pydantic models = DB models |
| Database | **SQLite** (dev) → PostgreSQL (prod) | Zero setup for dev |
| Server | **Uvicorn** | ASGI server for FastAPI |
| Package Mgr | **pip** + **requirements.txt** | Standard Python packaging |

### Frontend
| Layer | Technology | Notes |
|---|---|---|
| Framework | **Streamlit** | Single-file Python app, no build pipeline |
| HTTP Client | **requests** | Calls FastAPI backend directly |
| Charts | **pandas + st.bar_chart** | Score visualization in final report |
| Styling | Custom CSS via `st.markdown` | Professional light theme with injected CSS |

### Infrastructure
| Component | Tool |
|---|---|
| Version Control | Git + GitHub |
| Env Vars | `.env` (python-dotenv via pydantic-settings) |
| API Docs | FastAPI auto-generates Swagger at `/docs` |
| Knowledge Ingestion | `backend/scripts/ingest_knowledge.py` |
| Containerization | Docker multi-stage build + docker-compose.yml |

---

## Repository Structure (Current)

```
PrepLingo/
│
├── specs/                          ← All spec documents
│   ├── 00_project_overview.md
│   ├── 01_architecture.md
│   ├── 02_rag_design.md
│   ├── 03_techstack_and_repo.md    ← This file
│   ├── 04_data_models.md
│   ├── 05_langchain_chains.md
│   ├── 06_phase2_resume_pipeline.md
│   ├── 07_phase3_session_service.md
│   ├── 08_phase4_report_service.md
│   ├── 09_phase5_guest_mvp_hardening.md
│   ├── 10_manual_qa_checklist.md
│   ├── 11_testing_flow_guide.md
│   ├── 12_frontend_architecture_and_ux_plan.md
│   ├── 13_rag_knowledge_ingestion_and_content_plan.md
│   ├── 14_day_wise_worklog.md
│   └── DECISIONS.md
│
├── backend/                        ← FastAPI + LangChain
│   │
│   ├── app/
│   │   ├── main.py                 ← FastAPI app entry point
│   │   ├── config.py               ← Settings (env vars, model config) via pydantic-settings
│   │   │
│   │   ├── api/
│   │   │   ├── error_utils.py      ← Unified api_error() helper
│   │   │   └── routes/
│   │   │       ├── resume.py       ← /api/resume/upload, /api/resume/{id}/status, etc.
│   │   │       ├── session.py      ← /api/session/ CRUD + /start + /message + /end
│   │   │       └── report.py       ← /api/report/{session_id}
│   │   │
│   │   ├── services/               ← Business logic (no LangChain here)
│   │   │   ├── resume_service.py   ← parse_resume_with_llm(), embed_resume_for_rag()
│   │   │   ├── session_service.py  ← SessionService: orchestrates interview loop
│   │   │   └── report_service.py   ← ReportService: aggregates evaluations → report
│   │   │
│   │   ├── langchain_layer/        ← ALL LangChain/AI code lives here
│   │   │   │
│   │   │   ├── chains/
│   │   │   │   ├── question_chain.py    ← Generates next interview question (LCEL)
│   │   │   │   └── evaluation_chain.py  ← Scores user's answer (JsonOutputParser)
│   │   │   │
│   │   │   ├── prompts/            ← Prompt templates per interview type
│   │   │   │   ├── technical_prompt.py
│   │   │   │   ├── resume_interview_prompt.py
│   │   │   │   ├── system_design_prompt.py
│   │   │   │   └── behavioral_prompt.py
│   │   │   │
│   │   │   ├── retrievers/
│   │   │   │   └── dual_retriever.py    ← Resume chunks + Knowledge chunks
│   │   │   │
│   │   │   ├── memory/
│   │   │   │   └── session_memory.py    ← ConversationBufferWindowMemory per session
│   │   │   │
│   │   │   └── vector_store/
│   │   │       └── store_manager.py     ← ChromaDB init + HuggingFace embeddings
│   │   │
│   │   ├── models/                 ← SQLModel DB table definitions
│   │   │
│   │   └── db/
│   │       └── database.py         ← SQLite engine + session factory
│   │
│   ├── knowledge_base/             ← Curated markdown docs for RAG ingestion
│   │   ├── technical/
│   │   ├── system_design/
│   │   ├── behavioral/
│   │   └── resume_interview/
│   │
│   ├── knowledge_raw/              ← Auto-collected HTML/PDF sources (gitignored)
│   │   └── seed_sources.json       ← URLs for knowledge collection script
│   │
│   ├── scripts/
│   │   ├── ingest_knowledge.py          ← Embed all docs → ChromaDB
│   │   ├── collect_knowledge_sources.py ← Auto-download from seed URLs
│   │   ├── test_phase2_resume.py
│   │   ├── test_phase3_session.py
│   │   ├── test_phase4_report.py
│   │   ├── test_phase5_edge_cases.py
│   │   └── test_phase5_pdf_relevance.py
│   │
│   ├── vector_store_data/          ← ChromaDB persisted index (gitignored)
│   │
│   ├── Dockerfile                  ← Multi-stage: pre-downloads BAAI model at build time
│   ├── .env                        ← API keys, DB config (gitignored)
│   ├── .env.example                ← Template (committed)
│   └── requirements.txt
│
├── frontend_streamlit/             ← Streamlit frontend (MVP)
│   ├── app.py                      ← Single-file Streamlit app
│   └── .streamlit/
│       └── config.toml             ← Light theme config
│
├── docker-compose.yml              ← Orchestrates backend with volume persistence
├── .gitignore
└── README.md
```

---

## Key Design Rules

1. **LangChain code stays inside `langchain_layer/`** — services call langchain_layer, never import LangChain directly elsewhere
2. **One chain per responsibility** — `QuestionChain` and `EvaluationChain` are separate LCEL chains
3. **Prompts are versioned files** — one file per interview type in `prompts/`, no inline prompt strings
4. **Embedding model is locked to ChromaDB** — changing it requires a full reset + re-ingestion
5. **Knowledge base docs are human-readable** — `.md` files you can edit and understand
6. **Vector store data is gitignored** — always regenerated from source `.md` files via `ingest_knowledge.py`
7. **Error responses use unified shape** — `api_error()` in `error_utils.py` for all routes

---

## Environment Variables (`.env`)

```bash
# Required
GROQ_API_KEY=gsk_YOUR_KEY_HERE       # console.groq.com/keys (free)

# Optional (not needed since embeddings are local)
# GOOGLE_API_KEY only needed if you add Gemini-based resume parsing
GOOGLE_API_KEY=AIza_YOUR_KEY_HERE

# Model selection
GROQ_MODEL=llama-3.1-8b-instant       # or llama-3.3-70b-versatile for better quality
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5  # DO NOT change without resetting ChromaDB

# Database
DATABASE_URL=sqlite:///./preplingo.db  # Dev: SQLite; Prod: postgresql://...

# Auth (JWT — deferred to Phase 6)
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Storage
VECTOR_STORE_PATH=./vector_store_data

# App
APP_ENV=development
```
