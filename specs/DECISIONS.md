# PrepLingo — Finalized Decisions

**Status:** ✅ LOCKED (updated with Phase 2 learnings)

---

## All Decisions Confirmed

| # | Decision | Choice | Notes |
|---|---|---|---|
| 1 | LLM Provider | **Google Gemini** | Free tier, `ChatGoogleGenerativeAI` in LangChain |
| 2 | Embeddings | **`gemini-embedding-001`** | `text-embedding-004` deprecated — updated during Phase 2 |
| 3 | Vector Store | **ChromaDB** | Persistent, metadata filtering, LangChain native |
| 4 | CV in RAG | **Hybrid** (JSON summary + vector chunks) | JSON = overview, chunks = deep-dive retrieval |
| 5 | Evaluation timing | **Per answer (real-time)** | EvaluationChain runs after every user answer |
| 6 | Session length | **Fixed 8 questions** | Predictable UX, enough for meaningful report |
| 7 | Auth | **Guest mode first** | Focus on AI core, JWT auth added in Phase 5 |
| 8 | LangChain depth | **Full LCEL** | Modern LangChain standard, full learning value |
| 9 | Model config | **Centralized in `config.py`** | Change model in `.env` — no code changes needed |

---

## Phase 2 Update: Embedding Model Changed

**Was:** `models/text-embedding-004` (deprecated on v1beta API — returns 404)
**Now:** `models/gemini-embedding-001` (Google's current recommended model)

No quality difference for our use case. Same 768-dim vectors.

> ⚠️ **NEVER change the embedding model after knowledge base ingestion without resetting ChromaDB.**
> Different embedding models produce incompatible vectors. If you change it:
> 1. Delete `backend/vector_store_data/`
> 2. Run `python scripts/ingest_knowledge.py` again

---

## Phase 2 Update: Model Config Centralized

All model names now come from `config.py` / `.env` — zero code changes to switch models:

```env
# backend/.env
GEMINI_MODEL=gemini-2.0-flash-lite
EMBEDDING_MODEL=models/gemini-embedding-001
```

### Model Tier Guide

| Model | Free Quota | Quality | Use When |
|-------|-----------|---------|----------|
| `gemini-2.0-flash-lite` | Highest | Good | **Default for development** |
| `gemini-2.0-flash` | Medium | Better | Staging / demo |
| `gemini-2.5-flash` | Lowest | Best | Production with billing |

**Rate Limit Reality (Free Tier):**
- Each model has ~1,500 req/day free
- During heavy testing (embedding 35 chunks + multiple LLM calls), daily limit can be hit
- **Strategy:** quota resets daily at midnight UTC. Space out testing sessions.
- LangChain auto-retries with backoff on 429 errors — app never crashes, just slower

---

## Why Switching LLM Is Easy (LangChain's Power)

LangChain wraps every LLM behind the same `BaseChatModel` interface.
Your chains never talk to the LLM directly — they talk to LangChain.

```python
# TODAY: Gemini Flash Lite
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")

# TOMORROW: Switch to OpenAI — only THIS line changes
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini")

# ALL chains below stay IDENTICAL — they don't care which LLM you use
chain = prompt | llm | output_parser
```

This is the core value of LangChain. Your business logic is completely
decoupled from the LLM provider. One line swap = totally different provider.

---

## Google API Key Setup

1. Go to: https://aistudio.google.com/apikey
2. Generate a free API key
3. Add to `backend/.env`:
   ```
   GOOGLE_API_KEY=AIza...
   GEMINI_MODEL=gemini-2.0-flash-lite
   ```
4. This single key works for BOTH:
   - Gemini LLM (question generation + evaluation + resume parsing)
   - Gemini Embeddings (knowledge base + resume chunks in ChromaDB)
