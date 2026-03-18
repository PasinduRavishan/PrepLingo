# PrepLingo — Finalized Decisions

**Status:** ✅ LOCKED (updated through Phase 5 hardening session, 2026-03-17)

---

## All Decisions Confirmed

| # | Decision | Choice | Notes |
|---|---|---|---|
| 1 | LLM Provider | **Groq (Llama 3.1 8B Instant)** | Fast inference, no quota issues for interview loops |
| 2 | Embeddings | **BAAI/bge-base-en-v1.5 (local HuggingFace)** | 768 dims, MTEB 72.3 — better than Gemini (71.0). No API key, no rate limits. |
| 3 | Vector Store | **ChromaDB** | Persistent, metadata filtering, LangChain native |
| 4 | CV in RAG | **Hybrid** (structured semantic chunks + vector retrieval) | Chunks: identity+skills, one per project, experience, education |
| 5 | Evaluation timing | **Per answer (real-time)** | EvaluationChain runs after every user answer |
| 6 | Session length | **Fixed 8 questions** | Predictable UX, enough for meaningful report |
| 7 | Auth rollout | **Guest mode kept active** | JWT auth is deferred until post-MVP hardening |
| 8 | LangChain depth | **Full LCEL** | Modern LangChain standard, full learning value |
| 9 | Model config | **Centralized in `config.py`** | Change model in `.env` — no code changes needed |
| 10 | Report generation strategy | **Persisted, idempotent service** | Phase 4 uses cached report by default; supports forced regeneration |
| 11 | Frontend | **Streamlit** | Fast, Python-native, full-featured for MVP — no separate JS/TS build chain |
| 12 | Embedding deployment | **Pre-downloaded in Docker image** | Multi-stage build bakes BAAI model into image → zero cold-start download latency |

---

## Phase 5 Update: Embedding Model Changed (Gemini → BAAI/bge-base-en-v1.5)

**Was:** `models/gemini-embedding-001` (Google API — caused TimeoutError under load)
**Now:** `BAAI/bge-base-en-v1.5` via `langchain-huggingface` (local, no API calls)

**Root cause of the switch:**
After the first answer, two concurrent operations both called the Google Embedding API:
- The background CV embedding task (started on upload)
- The DualRetriever (which embeds the query to search ChromaDB)

The API contention caused a 25s TimeoutError on question generation — not a Groq rate limit.

**Quality gain:**
`BAAI/bge-base-en-v1.5` scores 72.3 on the MTEB benchmark vs Gemini embedding-001's ~71.0. 768 dimensions, identical vector shape. Vectors are also higher quality for technical/CS domain text.

> ⚠️ **NEVER change the embedding model after knowledge base ingestion without resetting ChromaDB.**
> Different embedding models produce incompatible vectors. If you change it:
> 1. Delete `backend/vector_store_data/`
> 2. Run `python scripts/ingest_knowledge.py` again

---

## Phase 5 Update: Frontend Changed (Next.js → Streamlit)

**Was:** Next.js 14 (App Router) — planned but not built
**Now:** `frontend_streamlit/app.py` — fully implemented Streamlit app

**Why Streamlit:**
- Rapid prototyping with full Python familiarity
- No separate build pipeline (no npm, no TypeScript, no bundler)
- First-class support for data display (metrics, charts, progress bars)
- Works instantly with the FastAPI backend via `requests`
- Styling via custom CSS injected via `st.markdown(unsafe_allow_html=True)`

**Streamlit frontend features implemented:**
- Light professional UI: warm ivory (`#f6f4ee`) + teal (`#0f766e`) + indigo (`#6366F1`) accents
- Step wizard: Upload CV → Configure → Interview → Report
- CV upload with background embedding status (manual refresh button)
- Interview type selection (4 clickable buttons)
- Q/A conversation timeline with color-coded score pills
- Custom progress bar (answered/total)
- Final report with big score, bar chart, and 3-column feedback grid
- Sidebar-less layout (control tower removed)

---

## Phase 5 Update: CV Embedding Flow Redesigned

**Was:** RecursiveCharacterTextSplitter on raw extracted text
**Now:** Structured semantic chunks built from LLM-parsed JSON

Chunk types (in order):
1. Identity + skills summary (`[Resume] Identity + Core Skills`)
2. One chunk per project (`[Resume] Project: <name>`)
3. Work experience narrative (`[Resume] Work Experience`)
4. Education (`[Resume] Education & Certifications`)

**Stale chunk deletion added:** Before inserting new embeddings, old chunks for the same `guest_id` are deleted from ChromaDB. This fixes the re-upload duplication bug.

**New endpoint added:** `GET /api/resume/{resume_id}/status` — lightweight polling endpoint the frontend calls to check when `chunks_embedded > 0`.

---

## Phase 5 Update: Evaluation Prompt Tuned

**Problem 1:** All scores were 0 — aggressive non-answer detection fired on real answers.
**Problem 2:** Inflated scores (5/10) for literal "cant" / "I don't know" responses.
**Fix:** Simplified to a single `SCORING GUIDE` block with clear anchors:

```
0:   Complete non-answer — literally "I don't know", "CANT", blank
2-3: Minimal — acknowledged the topic exists but no real explanation
4-5: Partial — shows some familiarity, missing key points
6-7: Good — correct understanding, could be deeper or clearer
8-9: Strong — thorough, well communicated, minor gaps only
10:  Excellent — comprehensive, clear, nothing missing
```

Framing changed to "friendly mock interview coach" to get balanced, encouraging feedback rather than harsh scores.

---

## Phase 5 Update: Repeated Greeting Bug Fixed

**Problem:** Every question started with "Hi, I'm your technical interviewer today."
**Root cause:** `{question_number}` was in the **system** template but NOT in the **human** template. The LLM never saw the number at turn time and re-introduced itself on every question.
**Fix:** Added `{question_number}` to the human template in all 4 prompt files with explicit rule: *"If question_number ≥ 2: output ONLY the question. No greeting. No introduction."*

---

## Phase 5 Update: Knowledge Ingestion Hardened

**Added filename filters** to skip noise files during ingestion:
- `_SKIP_STEMS`: `README`, `collector_README`, `discovery_report`, `seed_sources`, `seed_`, `index`
- `_SKIP_PREFIXES`: `seed_`, `index`

**Added content-hash deduplication:** Each document's text is hashed before embedding. Duplicate content (from seed_ copies) is skipped automatically with a warning log.

---

## API Keys Required

```env
# backend/.env — only these two are required
GROQ_API_KEY=gsk_YOUR_KEY_HERE       # From console.groq.com/keys (free)
# GOOGLE_API_KEY no longer needed for embeddings
```

> Note: `GOOGLE_API_KEY` is still in `config.py` as a field but is not used after the embedding model switch. You can set a dummy value or remove the field if not using Gemini resume parsing.

---

## Model Config Reference

```env
# backend/.env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant     # Default. Switch to llama-3.3-70b for better quality.
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5  # DO NOT change without resetting ChromaDB
DATABASE_URL=sqlite:///./preplingo.db
VECTOR_STORE_PATH=./vector_store_data
APP_ENV=development
```

### Groq Model Options

| Model | Latency | Quality | Use When |
|-------|---------|---------|----------|
| `llama-3.1-8b-instant` | ~0.5s | Good | **Default — development and demo** |
| `llama-3.3-70b-versatile` | ~2-4s | Best | Staging / production |
| `mixtral-8x7b-32768` | ~1s | Good | Long context scenarios |

All models on Groq's free tier: ~30 req/min, 14,400 req/day — more than enough for interview sessions.

---

## Why Switching LLM Is Easy (LangChain's Power)

LangChain wraps every LLM behind the same `BaseChatModel` interface:

```python
# TODAY: Groq Llama
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.1-8b-instant")

# TOMORROW: OpenAI GPT — only THIS line changes
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini")

# ALL chains stay IDENTICAL
chain = prompt | llm | output_parser
```
