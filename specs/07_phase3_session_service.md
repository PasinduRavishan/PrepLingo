# SPEC 07 — Phase 3 Implementation: Session Service & AI Loop

**Status:** ✅ IMPLEMENTED & TESTED
**Date:** 2026-03-12
**Files Created/Modified:**
- `backend/app/services/session_service.py` ← NEW (The core orchestrator)
- `backend/app/api/routes/session.py` ← UPDATED (Full endpoints)
- `backend/app/langchain_layer/chains/question_chain.py` ← UPDATED (Models)
- `backend/app/langchain_layer/chains/evaluation_chain.py` ← UPDATED (Models)
- `backend/app/langchain_layer/prompts/__init__.py` ← NEW
- `backend/scripts/test_phase3_session.py` ← NEW (Automated test)

---

## What Was Built

The core engine of the AI Interview Trainer is now fully functional. We built the complete LangChain LLM pipeline that powers the interview loop.

### 1. The Execution Pipeline (Per Message)

When a user submits an answer to a question, the backend runs this sequence:

1. **Load State:** Validates the session and retrieves conversation history from `SessionMemory`.
2. **Retrieve Context:** `DualRetriever` fetches both the candidate's resume data and domain knowledge rules related to the current topic.
3. **Evaluate (Async):** `EvaluationChain` uses Groq LLM to assess the candidate's answer based on the knowledge context, outputting strict JSON scores (0-10 for technical correctness, clarity, depth).
4. **Generate Next (Async):** `QuestionChain` uses Groq LLM to generate a relevant, personalized follow-up question.
5. **Persist State:** User message, AI question, and Evaluation scores are written to the SQLite DB.
6. **Progress:** The session question count is incremented.

### 2. Endpoints Implemented

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/session/` | Create a new session row (fast, sync) |
| `GET` | `/api/session/{id}/start` | Generates the opening question (slow, async) |
| `GET` | `/api/session/{id}` | Returns session state + all message history |
| `POST` | `/api/session/{id}/message` | The core loop: sends answer → gets evaluation + next Q |
| `POST` | `/api/session/{id}/end` | Early termination |

---

## 🚀 Huge Upgrade: Switched to Groq API

During Phase 3, we updated the underlying LLM provider from Google Gemini to **Groq**.

**Why the change?**
1. **Speed:** Groq uses specialized LPU hardware. Text generation is nearly instant. An interview feels like a real-time conversation instead of waiting 10 seconds per turn.
2. **Rate Limits:** Groq's developer tier handles parallel requests and high volume much better than the Gemini free tier, resolving the 429 quota exhaustion seen in Phase 2.
3. **Model:** We are now running Meta's **Llama 3.3 70B** model, the current state-of-the-art open source model, which excels at instruction following and structured JSON output.

> **Note:** We still use Google `gemini-embedding-001` for the vector embeddings in ChromaDB, as embeddings are highly reliable and rarely hit quotas.

---

## Test Results

The automated integration test (`scripts/test_phase3_session.py`) ran a full simulated interview.

```
✅ TEST 1: Health Check
✅ TEST 2: Create Session (type=technical)
✅ TEST 3: Get First Question (GET /start)
✅ TEST 4/2: Send Answer → Evaluated 4/10 + Next Question Gen'd
✅ TEST 4/3: Send Answer → Evaluated 4/10 + Next Question Gen'd
✅ TEST 5: Get Session History (verified 5 messages in DB)
✅ TEST 6: Validation — Can't call /start twice
✅ TEST 7: End Session
```

**Example AI Output Captured:**
> AI: "You've had experience with indexing in PostgreSQL. Can you explain the difference between a clustered index and a non-clustered index, and provide a scenario where you would choose to use each?"

**Example Evaluation Captured:**
> Overall: 4/10
> Technical Correctness: 2/10
> Clarity: 6/10
> Strengths: "Clearly explained database indexing..."
> Weaknesses: "Failed to address the main question about..."

---

## Technical Notes & Fixes

- **FastAPI Async Pipeline:** Built the `process_message` function using `await` for all LLM calls to ensure the server remains non-blocking during Groq API requests.
- **SQLModel Type Bug:** Fixed a bug in `session.py` where `db.get(type(..))` failed due to Python type annotations runtime behavior. Replaced with explicit static import.
- **Memory Handling:** In-memory `ConversationBufferWindowMemory` is correctly isolating session history using the session ID as a key.

## Next: Phase 4 — Report Service

Now that all evaluations and messages are cleanly stored in the database, the next step is to generate the final analytical report when the session completes (`session.question_count == 8`).
