# SPEC 14 - Day-wise Worklog

Status: Generated from repository evidence
Date: 2026-03-17

---

## Evidence Sources

1. Git commit history (author, date, message, files)
2. File modification dates for specs and scripts
3. Current working tree (uncommitted changes)
4. Session conversation logs

Note: This is an evidence-based log. It reflects what is visible in git and current files, not external notes or verbal work.

---

## 2026-03-12

**Project Inception & Core Infrastructure**

1. **Specs & Architecture Design** (Started ~12:00 PM):
   - Drafted `specs/00_project_overview.md` (Project goals & scope).
   - Defined `specs/01_architecture.md` (System layers).
   - Designed `specs/02_rag_design.md` (Retrieval strategy).
   - Set up technical baseline in `specs/03_techstack_and_repo.md`, `04_data_models.md`, and `05_langchain_chains.md`.

2. **Backend Initialization** (Started ~1:29 PM):
   - Initialized `backend/app/main.py` (FastAPI scaffold).
   - Configured environment management in `backend/app/config.py` and `backend/.env.example`.
   - Set up the initial `requirements.txt` with LangChain, FastAPI, and SQLAlchemy dependencies.

3. **Early Pipeline Simulation**:
   - Created `backend/scripts/test_phase2_resume.py` to define the resume ingestion logic.
   - Created `backend/scripts/test_phase3_session.py` to define the interview session flow.

Confidence: **High**. (Based on precise file creation timestamps: Specs at 12:00 PM, Code at 1:29 PM).

---

## 2026-03-13

Confirmed by commit 5873809 (message: upto phase 03 done):
1. Backend scaffold and architecture established
2. API routes and DB/model layers implemented
3. LangChain layer (prompts, retriever, chains, memory, vector store manager) added
4. Initial knowledge base markdown content added
5. Ingestion script and phase tests for resume/session added
6. Core specs and decisions doc added/updated

Representative files:
1. backend/app/main.py
2. backend/app/api/routes/resume.py
3. backend/app/api/routes/session.py
4. backend/app/langchain_layer/chains/question_chain.py
5. backend/app/langchain_layer/retrievers/dual_retriever.py
6. backend/scripts/ingest_knowledge.py

Confidence: high (commit evidence).

---

## 2026-03-16

Confirmed by commit ed47463 (message: phase 04 done):
1. Phase 4 report service and API behavior finalized
2. Session service/report integration updates
3. Phase 4 report test added
4. Specs updated for phase progress and decisions

Confirmed by file updates on same day:
1. Guest-mode hardening specs and QA guides added
   - specs/09_phase5_guest_mvp_hardening.md
   - specs/10_manual_qa_checklist.md
   - specs/11_testing_flow_guide.md
   - specs/12_frontend_architecture_and_ux_plan.md
   - specs/13_rag_knowledge_ingestion_and_content_plan.md
2. Phase 5 validation scripts added
   - backend/scripts/test_phase5_edge_cases.py
   - backend/scripts/test_phase5_pdf_relevance.py
3. Automated source collection assets added
   - backend/scripts/collect_knowledge_sources.py
   - backend/knowledge_raw/seed_sources.json
   - backend/knowledge_raw/collector_README.md

Confidence: high (commit plus file evidence).

---

## 2026-03-17

**Phase 5 Hardening Session — Full System Fixes + Streamlit Frontend**

A major working session that resolved all live issues found during end-to-end testing and delivered a complete Streamlit frontend. Changes are currently uncommitted.

### 1. Embedding Model Migration: Gemini → BAAI/bge-base-en-v1.5

**Problem:** After the first question-answer cycle, question generation started timing out (25s). Root cause: the background CV embedding task and the DualRetriever's query embedding were both hitting the Google Embedding API simultaneously, causing contention and a timeout. This was not a Groq rate limit.

**Fix:**
- Switched to `BAAI/bge-base-en-v1.5` via `langchain-huggingface` (local model, no API calls)
- Quality gain: MTEB 72.3 vs Gemini's ~71.0, same 768 dimensions
- Updated `backend/app/langchain_layer/vector_store/store_manager.py` (HuggingFaceEmbeddings)
- Updated `backend/app/config.py` (default `embedding_model = "BAAI/bge-base-en-v1.5"`)
- Added `langchain-huggingface` to `backend/requirements.txt`

**Docker support:**
- Created `backend/Dockerfile` (multi-stage build — downloads BAAI model at build time, zero cold-start)
- Created `docker-compose.yml` with named volumes for embedding cache and vector store persistence

### 2. CV Embedding Flow Redesign

**Problem:** Users had to wait for CV chunking and embedding before the interview could start. Background embedding was fast but retrieval quality was low (raw text splitting lost structure).

**Fix:**
- `resume_service.py`: `embed_resume_for_rag()` now accepts `parsed_data: dict | None`
- When `parsed_data` available: builds **structured semantic chunks** (identity+skills, one per project, experience, education) instead of raw text splitting
- Stale chunk deletion before re-upload: queries ChromaDB by `guest_id`, deletes old chunk IDs before inserting new ones (fixes re-upload duplication bug)
- New API endpoint: `GET /api/resume/{resume_id}/status` — lightweight polling for frontend
- Frontend shows manual "Refresh" button so user checks embedding status without blocking

### 3. Evaluation Scoring Fix

**Problem 1:** All evaluation scores were returning 0 for every answer.
**Root cause:** Over-aggressive non-answer detection rule ("STEP 1: check if answer contains only...") was incorrectly classifying real answers as non-answers and short-circuiting with all zeros.

**Problem 2:** Literal non-answers like "cant" were getting 5/10 with fabricated strengths like "showed basic understanding."

**Fix (3 iterations, final version):**
- Prompt reframed as "friendly mock interview coach" for balanced tone
- Replaced multi-step detection logic with a single clear `SCORING GUIDE` anchored at 0 / 2-3 / 4-5 / 6-7 / 8-9 / 10
- Rule: "Only give 0 if the candidate gave absolutely no answer (e.g. 'i dont know', 'cant remember', 'no'). For any genuine attempt, score at least 2-3."
- Files updated: `backend/app/langchain_layer/chains/evaluation_chain.py`

### 4. Repeated Greeting Bug Fix

**Problem:** Every AI question started with "Hi, I'm your technical interviewer today." — even questions 3, 5, 8.

**Root cause:** The `{question_number}` variable existed in the system prompt template but NOT in the human message template. The LLM never saw the number when generating its response, so it couldn't apply the "no greeting after Q1" rule.

**Fix:** Added `{question_number}` to the human template in ALL 4 prompt files with an explicit rule:
- `"If question_number is 1: introduce yourself with one sentence, then ask the question."`
- `"If question_number is 2 or higher: output ONLY the question. No greeting. No Hi. No self-introduction."`

Files updated:
- `backend/app/langchain_layer/prompts/technical_prompt.py`
- `backend/app/langchain_layer/prompts/resume_interview_prompt.py`
- `backend/app/langchain_layer/prompts/system_design_prompt.py`
- `backend/app/langchain_layer/prompts/behavioral_prompt.py`

### 5. Knowledge Ingestion Hardening

**Problem:** Admin files (README, collector_README, discovery_report), seed_ prefix files, and index pages were being ingested into ChromaDB, polluting knowledge retrieval with non-interview content.

**Fix in `backend/scripts/ingest_knowledge.py`:**
- Added `_SKIP_STEMS` frozenset: stems of filenames to skip (`README`, `collector_README`, `discovery_report`, `seed_sources`, `index`)
- Added `_SKIP_PREFIXES` tuple: filename prefixes to skip (`seed_`, `index`)
- Added `_should_skip_raw_file(path)` function applying both filters
- Updated `discover_files()` to accept `is_raw: bool` and apply filters only on `knowledge_raw/`
- Added content-hash deduplication: each file's text is hashed before embedding — duplicates skipped with a warning log

### 6. Process Resume Button Fix

**Problem:** The "Process Resume" button stopped responding after one click (multiple occurrences).

**Root cause:** The original button handler ended with `st.rerun()`, which on Streamlit's re-render caused the button's state to reset and not re-trigger. Additionally, a blocking `time.sleep()` polling loop in the frontend froze the Streamlit event loop.

**Fix:**
- Removed the blocking polling loop entirely
- Removed `st.rerun()` at the end of the button handler
- Replaced auto-poll with a simple manual "Refresh" button that calls `GET /api/resume/{id}/status`
- Added timeout-recovery logic: if upload times out, auto-calls `GET /api/resume/guest/{guest_id}` to recover the already-processed resume

### 7. Streamlit Frontend Built (Complete)

Implemented a full-featured professional frontend at `frontend_streamlit/app.py`. Replaced the "Control Tower" sidebar (which contained backend URL, guest ID management, and ping controls) with a cleaner in-page layout.

**Architecture:**
- Single `app.py` (no router, no components — Streamlit convention)
- `ensure_state()`: initializes all session state with safe defaults
- `reset_flow()`: resets interview state, preserves guest_id
- `inject_styles()`: CSS overrides for professional light theme
- `render_header()`: logo + API live badge + "↺ New Interview" button
- `resume_step()`: PDF upload, skills/projects display, embedding status
- `setup_session_step()`: interview type selection, session creation, first question trigger
- `interview_step()`: Q/A timeline with evaluation pills and feedback boxes
- `report_step()`: final report with big score, bar chart, 3-column feedback
- `_build_turns()`: pairs assistant/user messages by question_number for display

**Visual design:**
- Light professional theme: warm ivory `#f6f4ee`, teal `#0f766e`, indigo `#6366F1`
- Fonts: Fraunces (headings) + Space Grotesk (body) via Google Fonts
- Score pills: green (≥7) / amber (4-6) / red (<4)
- Config: `frontend_streamlit/.streamlit/config.toml` (light base, no sidebar)

### 8. Docs and Specs Updated

- `specs/DECISIONS.md` — updated to reflect all Phase 5 changes (embedding model, frontend, prompt fixes)
- `specs/03_techstack_and_repo.md` — updated tech stack table and repository structure
- `specs/12_frontend_architecture_and_ux_plan.md` — rewritten to document Streamlit implementation

Confidence: **High** (all changes in current working tree, reviewed end-to-end).

---

## 2026-03-18

**Full-Stack Production Deployment — GCP VPS with Docker Compose**

Today's session focused on productionising the entire PrepLingo application and deploying it to a live Google Cloud Platform virtual machine. The work spanned LLM configuration improvements, containerisation of the frontend, infrastructure composition, and iterative debugging of the full deployment pipeline.

### 1. LLM Upgrade — Primary/Fallback Model Strategy

Upgraded the primary language model from `llama-3.1-8b-instant` to `llama-3.3-70b-versatile` for significantly better question quality and evaluation accuracy. Implemented an automatic fallback mechanism using LangChain's built-in `with_fallbacks()` API so that if the primary model hits a rate limit (HTTP 429), the system transparently retries with the faster `llama-3.1-8b-instant` model without any user-facing error.

- Created `backend/app/langchain_layer/llm_factory.py` as a single LLM builder used by all chains
- Updated `QuestionChain`, `EvaluationChain`, and `ResumeService` to use the factory
- Added `GROQ_FALLBACK_MODEL` to `config.py` and `.env.example`

### 2. Frontend Containerisation

Containerised the Streamlit frontend by writing `frontend_streamlit/Dockerfile`. The frontend reads the backend URL from a `BACKEND_URL` environment variable (defaulting to `localhost` for local dev), injected by Docker Compose as `http://backend:8000` — the internal Docker network hostname. This ensures the frontend container calls the backend directly on the private network without going through nginx.

### 3. Full Docker Compose Architecture

Designed and implemented a three-service Docker Compose setup:

- **backend** — FastAPI + LangChain + ChromaDB, exposed only on the internal Docker network
- **frontend** — Streamlit app, also internal only, starts after backend passes health check
- **nginx** — Public-facing reverse proxy on port 80, routes `/api/*` to backend and `/*` to frontend with WebSocket upgrade support for Streamlit's live connection

Added named volumes for persistence: `embedding-cache` (HuggingFace model), `vector-data` (ChromaDB index), and `db-data` (SQLite database). Removed the `version` attribute from `docker-compose.yml` as it is now obsolete in Docker Compose v2.

### 4. Iterative Docker Build Debugging

Resolved a series of build and runtime issues encountered during deployment:

**Issue: `sentence-transformers` missing** — `langchain-huggingface` does not install `sentence-transformers` automatically; it is an unlisted optional dependency. Added it explicitly to `requirements.txt`.

**Issue: `uvicorn` not found in PATH** — The multi-stage Dockerfile copied `/usr/local/lib/python3.11/site-packages` but omitted `/usr/local/bin` where pip-installed executables live. Added `COPY --from=builder /usr/local/bin /usr/local/bin/`.

**Issue: SQLite "unable to open database file"** — The `db-data:/app` volume mount was shadowing the entire `/app` directory, hiding the application code on container restarts and preventing SQLite from writing. Fixed by changing the mount path to `/app/data` and updating `DATABASE_URL` to `sqlite:////app/data/preplingo.db`.

**Issue: Nginx "host not found in upstream"** — Nginx resolves upstream hostnames at startup, before the backend container is ready. Fixed by adding `resolver 127.0.0.11 valid=10s` (Docker's internal DNS) and declaring upstreams as `set $var` variables so resolution happens at request time rather than startup.

**Issue: Disk full on GCP VM** — `sentence-transformers` triggers installation of the full CUDA-enabled PyTorch build (~2.5 GB of nvidia-* libraries) even on a CPU-only server. Fixed by pre-installing CPU-only PyTorch using `pip install torch --index-url https://download.pytorch.org/whl/cpu` before the main `requirements.txt` install, reducing image size by approximately 2.3 GB.

**Issue: `knowledge_base/` not found in container** — The Dockerfile only copied `app/` and `scripts/`. Added `COPY knowledge_base/ ./knowledge_base/` to include the RAG knowledge documents.

**Issue: GCP firewall blocking port 80** — The VM was running correctly but incoming HTTP traffic was rejected by GCP's default network firewall. Created an `allow-http` firewall rule permitting TCP port 80 from all sources.

### 5. GCP VM Provisioned and Live

Provisioned a GCP Compute Engine `e2-medium` VM (2 vCPU, 4 GB RAM, 30 GB SSD, Ubuntu 22.04). Installed Docker via the official install script, cloned the repository, configured secrets in `.env`, ran the full Docker Compose build, and executed the knowledge base ingestion script inside the running backend container.

Application is live and accessible at the VM's public IP. All three containers — backend, frontend, and nginx — are running and healthy.

### 6. Documentation Updated

- `specs/15_deployment_guide.md` — comprehensive GCP deployment guide covering VM creation, Docker setup, ingestion, HTTPS, and day-to-day operations
- `specs/DECISIONS.md` — updated with LLM upgrade and fallback strategy
- `specs/03_techstack_and_repo.md` — updated repository structure and tech stack
- `.env.example` (root) — added for docker-compose secrets reference

Confidence: **High** (all changes deployed and verified live).

---

## Compact Timeline Summary

1. 2026-03-12: Foundation specs and early tests drafted
2. 2026-03-13: Phase 1 to 3 backend and RAG base implemented
3. 2026-03-16: Phase 4 completed, Phase 5 guest hardening/testing/specs expanded
4. 2026-03-17: Full system hardening — embedding migration, eval fixes, greeting bug, ingestion filters, complete Streamlit frontend built, docs updated
5. 2026-03-18: LLM upgrade with fallback, full Docker Compose with nginx, GCP VM provisioned and deployed live

---

## How to keep this day-wise automatically updated

1. Keep one commit per day with a clear message scope
2. Add a short daily note section in this file
3. Optionally add a script to generate date-grouped summary from git log
